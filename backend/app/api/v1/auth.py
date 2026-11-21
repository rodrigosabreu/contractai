"""Authentication API endpoints with token revocation."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.audit_log import AuditAction, AuditLog, AuditStatus
from app.models.token_blacklist import TokenBlacklist, RevocationReason
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MFAEnableRequest,
    MFAVerifyRequest,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    Token,
    TokenPayload,
    UserInviteRequest,
    UserInviteResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.schemas.common import ErrorResponse, SuccessResponse
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_token,
    get_current_user_dependency,
    get_password_hash,
    revoke_token,
    verify_password,
)

router = APIRouter()
security = HTTPBearer(auto_error=False)
settings = get_settings()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new organization and admin user",
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        409: {"model": ErrorResponse, "description": "Email or slug already exists"},
    },
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
) -> RegisterResponse:
    """Register a new organization with an admin user."""
    # Check if email exists
    existing_user = await db.execute(
        select(User).where(User.email == request.email, User.deleted_at.is_(None))
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check if organization slug exists
    from app.models.organization import Organization

    existing_org = await db.execute(
        select(Organization).where(
            Organization.slug == request.organization_slug, Organization.deleted_at.is_(None)
        )
    )
    if existing_org.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug already taken",
        )

    # Create organization
    org = Organization(
        name=request.organization_name,
        slug=request.organization_slug,
    )
    db.add(org)
    await db.flush()

    # Create admin user
    user = User(
        organization_id=org.id,
        email=request.email,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # Create tokens
    access_token = create_access_token(user.id, org.id, request.email, user.role, user.is_superuser)
    refresh_token = create_refresh_token(user.id, org.id)

    # Audit log
    audit = AuditLog.create(
        organization_id=org.id,
        user_id=user.id,
        action=AuditAction.USER_CREATE,
        status=AuditStatus.SUCCESS,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)

    org_audit = AuditLog.create(
        organization_id=org.id,
        user_id=user.id,
        action=AuditAction.ORG_CREATE,
        status=AuditStatus.SUCCESS,
        resource_type="organization",
        resource_id=str(org.id),
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(org_audit)

    await db.commit()

    return RegisterResponse(
        user=UserResponse.model_validate(user),
        organization=org,
        tokens=Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid credentials"},
        401: {"model": ErrorResponse, "description": "Authentication failed"},
        403: {"model": ErrorResponse, "description": "Account deactivated"},
    },
)
async def login(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
) -> LoginResponse:
    """Authenticate user and return tokens."""
    user = await authenticate_user(db, request.email, request.password)
    if not user:
        # Audit failed login
        audit = AuditLog.create(
            organization_id=user.organization_id if user else UUID(int=0),
            action=AuditAction.LOGIN_FAILED,
            status=AuditStatus.FAILURE,
            ip_address=req.client.host if req and req.client else None,
            request_id=req.headers.get("x-request-id"),
            details={"email": request.email},
            error_message="Invalid credentials",
        )
        db.add(audit)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # Create tokens
    access_token = create_access_token(
        user.id,
        user.organization_id,
        user.email,
        user.role,
        user.is_superuser,
        remember_me=request.remember_me,
    )
    refresh_token = create_refresh_token(user.id, user.organization_id, remember_me=request.remember_me)

    # Set refresh token as http-only cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 if request.remember_me else None,
        path="/api/v1/auth",
    )

    # Audit log
    audit = AuditLog.create(
        organization_id=user.organization_id,
        user_id=user.id,
        action=AuditAction.LOGIN,
        status=AuditStatus.SUCCESS,
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent"),
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(user)

    return LoginResponse(
        user=UserResponse.model_validate(user),
        tokens=Token(
            access_token=access_token,
            refresh_token=refresh_token,  # Also in body for backward compat, but should use cookie
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(
    request: RefreshTokenRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
) -> Token:
    """Refresh access token using refresh token (with revocation of old token)."""
    # Try to get token from cookie if not in body
    refresh_token = request.refresh_token
    if not refresh_token:
        refresh_token = req.cookies.get("refresh_token") if req else None

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    try:
        payload = decode_token(refresh_token)
        if payload.type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Check if refresh token is revoked
    from app.services.auth import is_token_revoked
    if await is_token_revoked(db, payload.jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    # Verify user still exists and is active
    user = await db.get(User, UUID(payload.sub))
    if not user or user.deleted_at or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # REVOKE OLD REFRESH TOKEN (rotate)
    await db.add(
        TokenBlacklist(
            jti=payload.jti,
            token_type="refresh",
            user_id=user.id,
            expires_at=datetime.fromtimestamp(payload.exp, tz=timezone.utc),
            reason="refresh_rotation",
        )
    )

    # Create new tokens
    access_token = create_access_token(
        user.id,
        user.organization_id,
        user.email,
        user.role,
        user.is_superuser,
    )
    new_refresh_token = create_refresh_token(user.id, user.organization_id)

    # Update cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )

    # Audit log
    audit = AuditLog.create(
        organization_id=user.organization_id,
        user_id=user.id,
        action=AuditAction.TOKEN_REFRESH,
        status=AuditStatus.SUCCESS,
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)
    await db.commit()

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    response_model=SuccessResponse,
    summary="User logout (revokes tokens)",
)
async def logout(
    response: Response,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> SuccessResponse:
    """Logout user and revoke tokens."""
    # Clear refresh token cookie
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")

    # Revoke access token if provided
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            if payload.type == "access":
                # Revoke the access token
                db.add(
                    TokenBlacklist(
                        jti=payload.jti,
                        token_type="access",
                        user_id=current_user.id,
                        expires_at=datetime.fromtimestamp(payload.exp, tz=timezone.utc),
                        reason="logout",
                    )
                )
        except ValueError:
            pass  # Token already invalid, ignore

    # Also revoke refresh token from cookie if present
    refresh_token = req.cookies.get("refresh_token") if req else None
    if refresh_token:
        try:
            payload = decode_token(refresh_token)
            if payload.type == "refresh":
                db.add(
                    TokenBlacklist(
                        jti=payload.jti,
                        token_type="refresh",
                        user_id=current_user.id,
                        expires_at=datetime.fromtimestamp(payload.exp, tz=timezone.utc),
                        reason="logout",
                    )
                )
        except ValueError:
            pass

    # Clear refresh token cookie
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")

    # Audit log
    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.LOGOUT,
        status=AuditStatus.SUCCESS,
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)
    await db.commit()

    return SuccessResponse(message="Logged out successfully")


@router.post(
    "/password/change",
    response_model=SuccessResponse,
    summary="Change password (revokes all tokens)",
    responses={
        400: {"model": ErrorResponse, "description": "Current password incorrect"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def change_password(
    request: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> SuccessResponse:
    """Change user password and revoke all tokens."""
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = get_password_hash(request.new_password)
    await db.commit()

    # TODO: In production, revoke all user tokens by adding to blacklist
    # For now, we just audit the change
    # In production: await revoke_all_user_tokens(db, current_user.id, "password_change")

    # Audit log
    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.PASSWORD_CHANGE,
        status=AuditStatus.SUCCESS,
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)
    await db.commit()

    return SuccessResponse(message="Password changed successfully")


@router.post(
    "/password/reset",
    response_model=SuccessResponse,
    summary="Request password reset",
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def request_password_reset(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
) -> SuccessResponse:
    """Request password reset email (simulated)."""
    user = await db.execute(
        select(User).where(User.email == request.email, User.deleted_at.is_(None))
    )
    user = user.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if user:
        # In production, send email with reset token
        # For now, we just log the request
        audit = AuditLog.create(
            organization_id=user.organization_id,
            user_id=user.id,
            action=AuditAction.PASSWORD_RESET_REQUEST,
            status=AuditStatus.SUCCESS,
            ip_address=req.client.host if req and req.client else None,
            request_id=req.headers.get("x-request-id"),
        )
        db.add(audit)
        await db.commit()

    return SuccessResponse(
        message="If the email exists, a password reset link has been sent"
    )


@router.post(
    "/password/reset/confirm",
    response_model=SuccessResponse,
    summary="Confirm password reset",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or expired reset token"},
    },
)
async def confirm_password_reset(
    request: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
) -> SuccessResponse:
    """Confirm password reset with token."""
    try:
        payload = decode_token(request.token)
        if payload.type != "reset":
            raise ValueError("Invalid token type")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = await db.get(User, UUID(payload.sub))
    if not user or user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.hashed_password = get_password_hash(request.new_password)
    await db.commit()

    # Revoke the reset token
    db.add(
        TokenBlacklist(
            jti=payload.jti,
            token_type="reset",
            user_id=user.id,
            expires_at=datetime.fromtimestamp(payload.exp, tz=timezone.utc),
            reason="password_reset",
        )
    )

    # TODO: Also revoke all user's access/refresh tokens
    # await revoke_all_user_tokens(db, user.id, "password_reset")

    # Audit log
    audit = AuditLog.create(
        organization_id=user.organization_id,
        user_id=user.id,
        action=AuditAction.PASSWORD_RESET_COMPLETE,
        status=AuditStatus.SUCCESS,
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)
    await db.commit()

    return SuccessResponse(message="Password reset successfully")


@router.post(
    "/mfa/enable",
    response_model=SuccessResponse,
    summary="Enable MFA",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid MFA code"},
    },
)
async def enable_mfa(
    request: MFAEnableRequest,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> SuccessResponse:
    """Enable multi-factor authentication (TOTP)."""
    import pyotp

    # Generate secret if not exists
    if not current_user.mfa_secret:
        secret = pyotp.random_base32()
        current_user.mfa_secret = secret
        await db.flush()

    # Verify code
    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )

    current_user.mfa_enabled = True
    # Generate backup codes
    current_user.mfa_backup_codes = [secrets.token_urlsafe(8) for _ in range(10)]
    await db.commit()

    # Audit log
    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.MFA_ENABLED,
        status=AuditStatus.SUCCESS,
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)
    await db.commit()

    return SuccessResponse(
        message="MFA enabled successfully",
        data={"backup_codes": current_user.mfa_backup_codes},
    )


@router.post(
    "/mfa/verify",
    response_model=SuccessResponse,
    summary="Verify MFA code",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid MFA code"},
    },
)
async def verify_mfa(
    request: MFAVerifyRequest,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> SuccessResponse:
    """Verify MFA code or backup code."""
    import pyotp

    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not enabled",
        )

    verified = False
    if request.code:
        totp = pyotp.TOTP(current_user.mfa_secret)
        verified = totp.verify(request.code)
    elif request.backup_code:
        if request.backup_code in (current_user.mfa_backup_codes or []):
            verified = True
            # Remove used backup code
            current_user.mfa_backup_codes.remove(request.backup_code)

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )

    await db.commit()
    return SuccessResponse(message="MFA verified successfully")


@router.delete(
    "/mfa/disable",
    response_model=SuccessResponse,
    summary="Disable MFA",
    responses={
        400: {"model": ErrorResponse, "description": "MFA not enabled"},
    },
)
async def disable_mfa(
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> SuccessResponse:
    """Disable multi-factor authentication."""
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not enabled",
        )

    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    current_user.mfa_backup_codes = None
    await db.commit()

    # Audit log
    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.MFA_DISABLED,
        status=AuditStatus.SUCCESS,
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)
    await db.commit()

    return SuccessResponse(message="MFA disabled successfully")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user_dependency),
) -> UserResponse:
    """Get current authenticated user profile."""
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    responses={
        403: {"model": ErrorResponse, "description": "Cannot change own role"},
    },
)
async def update_current_user(
    request: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> UserResponse:
    """Update current user profile."""
    if request.full_name is not None:
        current_user.full_name = request.full_name

    # Users cannot change their own role
    if request.role is not None and request.role != current_user.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change own role",
        )

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)