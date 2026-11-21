"""Connector API endpoints."""
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditAction, AuditLog, AuditStatus
from app.models.connector import Connector
from app.models.organization import Organization
from app.models.user import User
from app.schemas.common import ErrorResponse, PaginatedResponse, SuccessResponse
from app.schemas.connector import (
    ConnectorCreate,
    ConnectorListResponse,
    ConnectorResponse,
    ConnectorSyncRequest,
    ConnectorSyncResponse,
    ConnectorUpdate,
    GoogleDriveAuthRequest,
    GoogleDriveAuthResponse,
    OneDriveAuthRequest,
    OneDriveAuthResponse,
)
from app.services.auth import get_current_user_dependency

router = APIRouter()


async def _verify_organization_access(
    current_user: User, organization_id: UUID, db: AsyncSession
) -> None:
    """Verify user has access to the organization."""
    if current_user.organization_id != organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )


@router.post(
    "",
    response_model=ConnectorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new connector",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
    },
)
async def create_connector(
    request: ConnectorCreate,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> ConnectorResponse:
    """Create a new external storage connector."""
    await _verify_organization_access(current_user, current_user.organization_id, db)

    if request.credentials:
        raise HTTPException(status_code=501, detail="Connector credential storage is not implemented")
    connector = Connector(
        organization_id=current_user.organization_id,
        name=request.name,
        type=request.type,
        config=request.config,
        credentials=request.credentials,
        is_active=request.is_active,
    )
    db.add(connector)
    await db.flush()

    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.CONNECTOR_CREATE,
        resource_type="connector",
        resource_id=str(connector.id),
        status=AuditStatus.SUCCESS,
        details={"connector_name": connector.name, "connector_type": connector.type},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(connector)

    return ConnectorResponse.model_validate(connector)


@router.get(
    "",
    response_model=PaginatedResponse[ConnectorResponse],
    summary="List connectors",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
    },
)
async def list_connectors(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    type: str | None = Query(None, description="Filter by connector type"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> PaginatedResponse[ConnectorResponse]:
    """List connectors for the organization."""
    await _verify_organization_access(current_user, current_user.organization_id, db)

    query = select(Connector).where(
        Connector.organization_id == current_user.organization_id,
        Connector.deleted_at.is_(None),
    )
    if type:
        query = query.where(Connector.type == type)
    if is_active is not None:
        query = query.where(Connector.is_active == is_active)

    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    query = query.order_by(Connector.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    connectors = result.scalars().all()

    return PaginatedResponse.create(
        items=[ConnectorResponse.model_validate(c) for c in connectors],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{connector_id}",
    response_model=ConnectorResponse,
    summary="Get connector by ID",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Connector not found"},
    },
)
async def get_connector(
    connector_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> ConnectorResponse:
    """Get a specific connector."""
    await _verify_organization_access(current_user, current_user.organization_id, db)

    connector = await db.get(Connector, connector_id)
    if not connector or connector.deleted_at or connector.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")

    return ConnectorResponse.model_validate(connector)


@router.patch(
    "/{connector_id}",
    response_model=ConnectorResponse,
    summary="Update connector",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Connector not found"},
    },
)
async def update_connector(
    connector_id: UUID,
    request: ConnectorUpdate,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> ConnectorResponse:
    """Update a connector."""
    await _verify_organization_access(current_user, current_user.organization_id, db)

    connector = await db.get(Connector, connector_id)
    if not connector or connector.deleted_at or connector.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")

    update_data = request.model_dump(exclude_unset=True)
    if update_data.get("credentials"):
        raise HTTPException(status_code=501, detail="Connector credential storage is not implemented")
    for field, value in update_data.items():
        setattr(connector, field, value)

    connector.updated_at = datetime.now(connector.created_at.tzinfo)

    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.CONNECTOR_UPDATE,
        resource_type="connector",
        resource_id=str(connector.id),
        status=AuditStatus.SUCCESS,
        details={"updated_fields": list(update_data.keys())},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(connector)

    return ConnectorResponse.model_validate(connector)


@router.delete(
    "/{connector_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete connector (soft delete)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Connector not found"},
    },
)
async def delete_connector(
    connector_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> None:
    """Soft delete a connector."""
    await _verify_organization_access(current_user, current_user.organization_id, db)

    connector = await db.get(Connector, connector_id)
    if not connector or connector.deleted_at or connector.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")

    connector.deleted_at = datetime.now(connector.created_at.tzinfo)
    connector.is_active = False

    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.CONNECTOR_DELETE,
        resource_type="connector",
        resource_id=str(connector.id),
        status=AuditStatus.SUCCESS,
        details={"connector_name": connector.name},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()


@router.post(
    "/{connector_id}/sync",
    response_model=ConnectorSyncResponse,
    summary="Sync connector files",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Connector not found"},
        409: {"model": ErrorResponse, "description": "Connector not active"},
    },
)
async def sync_connector(
    connector_id: UUID,
    request: ConnectorSyncRequest,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> ConnectorSyncResponse:
    """Trigger connector synchronization."""
    await _verify_organization_access(current_user, current_user.organization_id, db)

    connector = await db.get(Connector, connector_id)
    if not connector or connector.deleted_at or connector.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")

    if not connector.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connector is not active")

    raise HTTPException(status_code=501, detail="Connector synchronization is not implemented")

    # TODO: Implement actual sync logic with connector services
    # This would call GoogleDriveService or OneDriveService
    synced_count = 0
    errors = []

    connector.last_sync_at = datetime.now(connector.created_at.tzinfo)

    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.CONNECTOR_SYNC,
        resource_type="connector",
        resource_id=str(connector.id),
        status=AuditStatus.SUCCESS if not errors else AuditStatus.PARTIAL,
        details={"synced_count": synced_count, "errors": errors},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()

    return ConnectorSyncResponse(
        connector_id=connector.id,
        synced_count=synced_count,
        errors=errors,
        synced_at=connector.last_sync_at,
    )


@router.get(
    "/google/auth",
    response_model=GoogleDriveAuthResponse,
    summary="Get Google Drive OAuth URL",
)
async def google_drive_auth_url(
    request: GoogleDriveAuthRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> GoogleDriveAuthResponse:
    """Get Google Drive OAuth authorization URL."""
    raise HTTPException(status_code=501, detail="Google OAuth is not implemented")


@router.get(
    "/google/callback",
    summary="Google Drive OAuth callback",
)
async def google_drive_callback(
    code: str,
    state: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict:
    """Handle Google Drive OAuth callback."""
    raise HTTPException(status_code=501, detail="Google OAuth is not implemented")


@router.get(
    "/onedrive/auth",
    response_model=OneDriveAuthResponse,
    summary="Get OneDrive OAuth URL",
)
async def onedrive_auth_url(
    request: OneDriveAuthRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> OneDriveAuthResponse:
    """Get OneDrive OAuth authorization URL."""
    raise HTTPException(status_code=501, detail="OneDrive OAuth is not implemented")


@router.get(
    "/onedrive/callback",
    summary="OneDrive OAuth callback",
)
async def onedrive_callback(
    code: str,
    state: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict:
    """Handle OneDrive OAuth callback."""
    raise HTTPException(status_code=501, detail="OneDrive OAuth is not implemented")