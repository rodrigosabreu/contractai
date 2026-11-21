"""Contract API endpoints."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.audit_log import AuditAction, AuditLog, AuditStatus
from app.models.contract import Contract, ContractSource, ContractStatus
from app.models.user import User
from app.schemas.common import ErrorResponse, PaginatedResponse, SuccessResponse
from app.schemas.contract import (
    ContractCreate,
    ContractListResponse,
    ContractResponse,
    ContractUpdate,
    ContractUploadResponse,
)
from app.services.auth import get_current_user_dependency

router = APIRouter()
settings = get_settings()


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
    "/upload",
    response_model=ContractUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new contract",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file"},
        403: {"model": ErrorResponse, "description": "Access denied"},
        413: {"model": ErrorResponse, "description": "File too large"},
    },
)
async def upload_contract(
    file: Annotated[UploadFile, File(description="Contract file (PDF, DOCX, TXT)")],
    title: Annotated[str, Form(max_length=500)],
    description: Annotated[str | None, Form(max_length=5000)] = None,
    source: Annotated[ContractSource, Form()] = ContractSource.UPLOAD,
    source_id: Annotated[str | None, Form(max_length=255)] = None,
    source_url: Annotated[str | None, Form(max_length=1000)] = None,
    language: Annotated[str, Form(max_length=10)] = "pt-BR",
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> ContractUploadResponse:
    """Upload a new contract document."""
    # Verify organization access
    await _verify_organization_access(current_user, current_user.organization_id, db)

    # Validate file
    allowed_extensions = {ext.strip().lower() for ext in settings.ALLOWED_EXTENSIONS.split(",")}
    file_extension = file.filename.split(".")[-1].lower() if file.filename else ""
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}",
        )

    # Read file content
    content = await file.read()
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Create contract record
    contract = Contract(
        organization_id=current_user.organization_id,
        owner_id=current_user.id,
        title=title,
        description=description,
        source=source,
        source_id=source_id,
        source_url=source_url,
        file_size=len(content),
        mime_type=file.content_type,
        language=language,
        status=ContractStatus.UPLOADED,
    )
    db.add(contract)
    await db.flush()

    # Save file to disk
    import os
    import hashlib

    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    content_hash = hashlib.sha256(content).hexdigest()
    file_path = os.path.join(upload_dir, f"{contract.id}_{content_hash[:16]}.{file_extension}")

    with open(file_path, "wb") as f:
        f.write(content)

    contract.file_path = file_path
    contract.content_hash = content_hash
    contract.status = ContractStatus.PARSED

    # Extract text content (basic implementation)
    if file_extension == "txt":
        contract.content_text = content.decode("utf-8", errors="ignore")
    elif file_extension == "pdf":
        try:
            import pypdf
            import io

            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            contract.content_text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
            contract.page_count = len(pdf_reader.pages)
        except Exception:
            contract.content_text = ""
    elif file_extension == "docx":
        try:
            import docx
            import io

            doc = docx.Document(io.BytesIO(content))
            contract.content_text = "\n".join(para.text for para in doc.paragraphs)
        except Exception:
            contract.content_text = ""

    # Audit log
    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.CONTRACT_UPLOAD,
        status=AuditStatus.SUCCESS,
        resource_type="contract",
        resource_id=str(contract.id),
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
        details={"title": title, "file_size": len(content), "source": source.value},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(contract)

    return ContractUploadResponse(
        contract=ContractResponse.model_validate(contract),
        upload_id=str(contract.id),
        status=contract.status,
        message="Contract uploaded successfully",
    )


@router.get(
    "",
    response_model=ContractListResponse,
    summary="List contracts",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
    },
)
async def list_contracts(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[ContractStatus | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> ContractListResponse:
    """List contracts for the current organization."""
    # Verify organization access
    await _verify_organization_access(current_user, current_user.organization_id, db)

    # Build query
    query = select(Contract).where(
        Contract.organization_id == current_user.organization_id,
        Contract.deleted_at.is_(None),
    )
    if status_filter:
        query = query.where(Contract.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination
    query = query.order_by(Contract.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    contracts = result.scalars().all()

    # Build response
    contract_responses = [ContractResponse.model_validate(c) for c in contracts]
    total_pages = (total + page_size - 1) // page_size

    return ContractListResponse(
        contracts=contract_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.get(
    "/{contract_id}",
    response_model=ContractResponse,
    summary="Get contract by ID",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Contract not found"},
    },
)
async def get_contract(
    contract_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> ContractResponse:
    """Get a contract by ID."""
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    await _verify_organization_access(current_user, contract.organization_id, db)

    # Audit log
    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.CONTRACT_VIEW,
        status=AuditStatus.SUCCESS,
        resource_type="contract",
        resource_id=str(contract.id),
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)
    await db.commit()

    return ContractResponse.model_validate(contract)


@router.patch(
    "/{contract_id}",
    response_model=ContractResponse,
    summary="Update contract metadata",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Contract not found"},
    },
)
async def update_contract(
    contract_id: UUID,
    request: ContractUpdate,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> ContractResponse:
    """Update contract metadata."""
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    await _verify_organization_access(current_user, contract.organization_id, db)

    # Update fields
    if request.title is not None:
        contract.title = request.title
    if request.description is not None:
        contract.description = request.description
    if request.language is not None:
        contract.language = request.language
    if request.meta is not None:
        contract.meta = request.meta

    # Audit log
    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.CONTRACT_UPDATE,
        status=AuditStatus.SUCCESS,
        resource_type="contract",
        resource_id=str(contract.id),
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
        details=request.model_dump(exclude_unset=True),
    )
    db.add(audit)

    await db.commit()
    await db.refresh(contract)

    return ContractResponse.model_validate(contract)


@router.delete(
    "/{contract_id}",
    response_model=SuccessResponse,
    summary="Delete contract (soft delete)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Contract not found"},
    },
)
async def delete_contract(
    contract_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> SuccessResponse:
    """Soft delete a contract."""
    from datetime import datetime, timezone

    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    await _verify_organization_access(current_user, contract.organization_id, db)

    contract.deleted_at = datetime.now(timezone.utc)

    # Audit log
    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.CONTRACT_DELETE,
        status=AuditStatus.SUCCESS,
        resource_type="contract",
        resource_id=str(contract.id),
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)

    await db.commit()

    return SuccessResponse(message="Contract deleted successfully")


@router.post(
    "/{contract_id}/restore",
    response_model=SuccessResponse,
    summary="Restore deleted contract",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Contract not found"},
    },
)
async def restore_contract(
    contract_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> SuccessResponse:
    """Restore a soft-deleted contract."""
    contract = await db.get(Contract, contract_id)
    if not contract or not contract.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found or not deleted")

    await _verify_organization_access(current_user, contract.organization_id, db)

    contract.deleted_at = None

    # Audit log
    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.CONTRACT_RESTORE,
        status=AuditStatus.SUCCESS,
        resource_type="contract",
        resource_id=str(contract.id),
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)

    await db.commit()

    return SuccessResponse(message="Contract restored successfully")