"""Organization API endpoints."""
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditAction, AuditLog, AuditStatus
from app.models.organization import Organization, OrganizationPlan
from app.models.user import User, UserRole
from app.schemas.common import ErrorResponse, PaginatedResponse, SuccessResponse
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationListResponse,
    OrganizationResponse,
    OrganizationSettingsUpdate,
    OrganizationUpdate,
    UserInviteRequest,
    UserInviteResponse,
)
from app.services.auth import get_current_user_dependency, get_password_hash

router = APIRouter()


async def _verify_admin_access(
    current_user: User, organization_id: UUID, db: AsyncSession
) -> None:
    """Verify user has admin access to the organization."""
    if current_user.organization_id != organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER) and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or manager role required",
        )


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new organization",
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        409: {"model": ErrorResponse, "description": "Slug already exists"},
    },
)
async def create_organization(
    request: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> OrganizationResponse:
    """Create a new organization (superuser only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can create organizations",
        )

    # Check slug uniqueness
    existing = await db.execute(
        select(Organization).where(Organization.slug == request.slug, Organization.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug already exists",
        )

    org = Organization(
        name=request.name,
        slug=request.slug,
        plan=request.plan,
        settings=request.settings,
        is_single_tenant=False,
    )
    db.add(org)
    await db.flush()

    # Create admin user for the org if needed (or link current user)
    # For now, we just create the org

    audit = AuditLog.create(
        organization_id=org.id,
        user_id=current_user.id,
        action=AuditAction.ORG_CREATE,
        resource_type="organization",
        resource_id=str(org.id),
        status=AuditStatus.SUCCESS,
        details={"name": org.name, "slug": org.slug, "plan": org.plan.value},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(org)

    return OrganizationResponse.model_validate(org)


@router.get(
    "",
    response_model=PaginatedResponse[OrganizationResponse],
    summary="List organizations (superuser only)",
    responses={
        403: {"model": ErrorResponse, "description": "Superuser access required"},
    },
)
async def list_organizations(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    plan: str | None = Query(None, description="Filter by plan"),
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> PaginatedResponse[OrganizationResponse]:
    """List all organizations (superuser only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )

    query = select(Organization).where(Organization.deleted_at.is_(None))
    if plan:
        query = query.where(Organization.plan == plan)

    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    query = query.order_by(Organization.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    orgs = result.scalars().all()

    # Add computed counts
    responses = []
    for org in orgs:
        user_count = await db.scalar(
            select(func.count()).where(
                User.organization_id == org.id,
                User.deleted_at.is_(None),
            )
        ) or 0
        contract_count = await db.scalar(
            select(func.count()).where(
                Contract.organization_id == org.id,
                Contract.deleted_at.is_(None),
            )
        ) or 0
        analysis_count = await db.scalar(
            select(func.count()).where(
                Analysis.organization_id == org.id,
                Analysis.deleted_at.is_(None),
            )
        ) or 0

        org_resp = OrganizationResponse.model_validate(org)
        org_resp.user_count = user_count
        org_resp.contract_count = contract_count
        org_resp.analysis_count = analysis_count
        responses.append(org_resp)

    return PaginatedResponse.create(
        items=responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/me",
    response_model=OrganizationResponse,
    summary="Get current user's organization",
)
async def get_my_organization(
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> OrganizationResponse:
    """Get the current user's organization."""
    org = await db.get(Organization, current_user.organization_id)
    if not org or org.deleted_at:
        raise HTTPException(status_code=404, detail="Organization not found")

    user_count = await db.scalar(
        select(func.count()).where(
            User.organization_id == org.id,
            User.deleted_at.is_(None),
        )
    ) or 0
    contract_count = await db.scalar(
        select(func.count()).where(
            Contract.organization_id == org.id,
            Contract.deleted_at.is_(None),
        )
    ) or 0
    analysis_count = await db.scalar(
        select(func.count()).where(
            Analysis.organization_id == org.id,
            Analysis.deleted_at.is_(None),
        )
    ) or 0

    org_resp = OrganizationResponse.model_validate(org)
    org_resp.user_count = user_count
    org_resp.contract_count = contract_count
    org_resp.analysis_count = analysis_count

    return org_resp


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
    summary="Get organization by ID (superuser or org member)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Organization not found"},
    },
)
async def get_organization(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> OrganizationResponse:
    """Get a specific organization."""
    if not current_user.is_superuser and current_user.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    org = await db.get(Organization, organization_id)
    if not org or org.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    return OrganizationResponse.model_validate(org)


@router.patch(
    "/{organization_id}",
    response_model=OrganizationResponse,
    summary="Update organization (admin/superuser)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Organization not found"},
    },
)
async def update_organization(
    organization_id: UUID,
    request: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> OrganizationResponse:
    """Update an organization."""
    if not current_user.is_superuser:
        await _verify_admin_access(current_user, organization_id, db)

    org = await db.get(Organization, organization_id)
    if not org or org.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)

    org.updated_at = datetime.now(org.created_at.tzinfo)

    audit = AuditLog.create(
        organization_id=organization_id,
        user_id=current_user.id,
        action=AuditAction.ORG_UPDATE,
        resource_type="organization",
        resource_id=str(org.id),
        status=AuditStatus.SUCCESS,
        details={"updated_fields": list(update_data.keys())},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(org)

    return OrganizationResponse.model_validate(org)


@router.patch(
    "/{organization_id}/settings",
    response_model=OrganizationResponse,
    summary="Update organization settings (admin/superuser)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Organization not found"},
    },
)
async def update_organization_settings(
    organization_id: UUID,
    request: OrganizationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> OrganizationResponse:
    """Update organization settings."""
    if not current_user.is_superuser:
        await _verify_admin_access(current_user, organization_id, db)

    org = await db.get(Organization, organization_id)
    if not org or org.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    org.settings = {**org.settings, **request.settings}
    org.updated_at = datetime.now(org.created_at.tzinfo)

    audit = AuditLog.create(
        organization_id=organization_id,
        user_id=current_user.id,
        action=AuditAction.ORG_SETTINGS_CHANGE,
        resource_type="organization",
        resource_id=str(org.id),
        status=AuditStatus.SUCCESS,
        details={"settings_keys": list(request.settings.keys())},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(org)

    return OrganizationResponse.model_validate(org)


@router.post(
    "/{organization_id}/invite",
    response_model=UserInviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite user to organization (admin/superuser)",
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        403: {"model": ErrorResponse, "description": "Access denied"},
        409: {"model": ErrorResponse, "description": "User already exists"},
    },
)
async def invite_user(
    organization_id: UUID,
    request: UserInviteRequest,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> UserInviteResponse:
    """Invite a new user to the organization."""
    if not current_user.is_superuser:
        await _verify_admin_access(current_user, organization_id, db)

    # Check if user already exists
    existing = await db.execute(
        select(User).where(User.email == request.email, User.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    # Generate temporary password
    import secrets
    temp_password = secrets.token_urlsafe(12)
    hashed_password = get_password_hash(temp_password)

    user = User(
        organization_id=organization_id,
        email=request.email,
        hashed_password=hashed_password,
        full_name=request.full_name,
        role=request.role,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    audit = AuditLog.create(
        organization_id=organization_id,
        user_id=current_user.id,
        action=AuditAction.USER_CREATE,
        resource_type="user",
        resource_id=str(user.id),
        status=AuditStatus.SUCCESS,
        details={"email": user.email, "role": user.role.value, "invited": True},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()

    # TODO: Send invitation email with temp password

    return UserInviteResponse(
        user_id=user.id,
        email=user.email,
        temporary_password=temp_password,
        message="User invited successfully. Share the temporary password securely.",
    )


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete organization (superuser only, soft delete)",
    responses={
        403: {"model": ErrorResponse, "description": "Superuser access required"},
        404: {"model": ErrorResponse, "description": "Organization not found"},
    },
)
async def delete_organization(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> None:
    """Soft delete an organization (superuser only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )

    org = await db.get(Organization, organization_id)
    if not org or org.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    org.deleted_at = datetime.now(org.created_at.tzinfo)

    audit = AuditLog.create(
        organization_id=organization_id,
        user_id=current_user.id,
        action=AuditAction.ORG_DELETE,
        resource_type="organization",
        resource_id=str(org.id),
        status=AuditStatus.SUCCESS,
        details={"name": org.name},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()


# Import models needed
from app.models.contract import Contract
from app.models.analysis import Analysis