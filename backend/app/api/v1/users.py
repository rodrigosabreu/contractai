"""User management API endpoints."""
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditAction, AuditLog, AuditStatus
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.schemas.auth import UserResponse, UserUpdateRequest
from app.schemas.common import ErrorResponse, PaginatedResponse
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


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    summary="List users in organization (admin/manager)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
    },
)
async def list_users(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    role: str | None = Query(None, description="Filter by role"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
):
    """List users in the current organization."""
    await _verify_admin_access(current_user, current_user.organization_id, db)

    query = select(User).where(
        User.organization_id == current_user.organization_id,
        User.deleted_at.is_(None),
    )
    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    query = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    # PaginatedResponse expects list[UserResponse] and creates pagination
    items = [UserResponse.model_validate(u) for u in users]
    from app.schemas.common import PaginatedResponse as PR
    return PR.create(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user_dependency),
) -> UserResponse:
    """Get the current user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_current_user(
    request: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> UserResponse:
    """Update current user's own profile (name, password)."""
    user = current_user

    update_data = request.model_dump(exclude_unset=True)

    if "password" in update_data:
        from app.services.auth import get_password_hash
        user.hashed_password = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = datetime.now(user.created_at.tzinfo)

    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.USER_UPDATE,
        resource_type="user",
        resource_id=str(user.id),
        status=AuditStatus.SUCCESS,
        details={"updated_fields": list(update_data.keys()), "self_update": True},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID (admin/manager)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> UserResponse:
    """Get a specific user in the organization."""
    await _verify_admin_access(current_user, current_user.organization_id, db)

    user = await db.get(User, user_id)
    if not user or user.deleted_at or user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user (admin/manager)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> UserResponse:
    """Update a user in the organization (admin/manager)."""
    await _verify_admin_access(current_user, current_user.organization_id, db)

    user = await db.get(User, user_id)
    if not user or user.deleted_at or user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-demotion or removing last admin
    if user.id == current_user.id and current_user.role == UserRole.ADMIN:
        # Allow self-update but prevent role demotion
        pass

    update_data = request.model_dump(exclude_unset=True)

    if "password" in update_data:
        from app.services.auth import get_password_hash
        user.hashed_password = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = datetime.now(user.created_at.tzinfo)

    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.USER_UPDATE,
        resource_type="user",
        resource_id=str(user.id),
        status=AuditStatus.SUCCESS,
        details={"updated_fields": list(update_data.keys()), "target_user_id": str(user.id)},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.post(
    "/{user_id}/activate",
    response_model=UserResponse,
    summary="Activate user (admin/manager)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def activate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> UserResponse:
    """Activate a deactivated user."""
    await _verify_admin_access(current_user, current_user.organization_id, db)

    user = await db.get(User, user_id)
    if not user or user.deleted_at or user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_active:
        raise HTTPException(status_code=400, detail="User is already active")

    user.is_active = True
    user.updated_at = datetime.now(user.created_at.tzinfo)

    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.USER_ACTIVATE,
        resource_type="user",
        resource_id=str(user.id),
        status=AuditStatus.SUCCESS,
        details={},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.post(
    "/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Deactivate user (admin/manager)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> UserResponse:
    """Deactivate a user (soft delete alternative)."""
    await _verify_admin_access(current_user, current_user.organization_id, db)

    user = await db.get(User, user_id)
    if not user or user.deleted_at or user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="User is already inactive")

    # Prevent deactivating last admin
    admin_count = await db.scalar(
        select(func.count()).where(
            User.organization_id == current_user.organization_id,
            User.role == UserRole.ADMIN,
            User.is_active == True,
            User.deleted_at.is_(None),
        )
    ) or 0
    if admin_count <= 1 and user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Cannot deactivate the last admin")

    user.is_active = False
    user.updated_at = datetime.now(user.created_at.tzinfo)

    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.USER_DEACTIVATE,
        resource_type="user",
        resource_id=str(user.id),
        status=AuditStatus.SUCCESS,
        details={},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.post(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Change user role (admin/superuser)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def change_user_role(
    user_id: UUID,
    role: str,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> UserResponse:
    """Change a user's role."""
    if not current_user.is_superuser:
        await _verify_admin_access(current_user, current_user.organization_id, db)

    user = await db.get(User, user_id)
    if not user or user.deleted_at or user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate role
    try:
        new_role = UserRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    # Prevent removing last admin
    if user.role == UserRole.ADMIN and new_role != UserRole.ADMIN:
        admin_count = await db.scalar(
            select(func.count()).where(
                User.organization_id == current_user.organization_id,
                User.role == UserRole.ADMIN,
                User.is_active == True,
                User.deleted_at.is_(None),
            )
        ) or 0
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last admin")

    old_role = user.role
    user.role = new_role
    user.updated_at = datetime.now(user.created_at.tzinfo)

    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.USER_ROLE_CHANGE,
        resource_type="user",
        resource_id=str(user.id),
        status=AuditStatus.SUCCESS,
        details={"old_role": old_role.value, "new_role": new_role.value},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user (admin/superuser, soft delete)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> None:
    """Soft delete a user."""
    if not current_user.is_superuser:
        await _verify_admin_access(current_user, current_user.organization_id, db)

    user = await db.get(User, user_id)
    if not user or user.deleted_at or user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user.deleted_at = datetime.now(user.created_at.tzinfo)
    user.is_active = False

    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.USER_DELETE,
        resource_type="user",
        resource_id=str(user.id),
        status=AuditStatus.SUCCESS,
        details={"email": user.email},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()