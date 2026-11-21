"""Authentication service with JWT token management and token revocation."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.token_blacklist import TokenBlacklist
from app.models.user import User
from app.schemas.auth import TokenPayload

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

security = HTTPBearer(auto_error=False)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: UUID,
    organization_id: UUID,
    email: str,
    role: str,
    is_superuser: bool = False,
    remember_me: bool = False,
) -> str:
    """Create JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "org_id": str(organization_id),
        "email": email,
        "role": role,
        "is_superuser": is_superuser,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "type": "access",
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    user_id: UUID,
    organization_id: UUID,
    remember_me: bool = False,
) -> str:
    """Create JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(user_id),
        "org_id": str(organization_id),
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_reset_token(user_id: UUID, organization_id: UUID) -> str:
    """Create password reset token (1 hour expiry)."""
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {
        "sub": str(user_id),
        "org_id": str(organization_id),
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "type": "reset",
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> Optional[User]:
    """Authenticate user with email and password."""
    result = await db.execute(
        select(User).where(
            User.email == email,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def is_token_revoked(db: AsyncSession, jti: str) -> bool:
    """Check if a token is revoked (blacklisted)."""
    result = await db.execute(
        select(TokenBlacklist).where(TokenBlacklist.jti == jti)
    )
    return result.scalar_one_or_none() is not None


async def revoke_token(
    db: AsyncSession,
    jti: str,
    token_type: str,
    user_id: UUID,
    expires_at: datetime,
    reason: str = "revoked",
) -> TokenBlacklist:
    """Add token to blacklist."""
    blacklist_entry = TokenBlacklist(
        jti=jti,
        token_type=token_type,
        user_id=user_id,
        expires_at=expires_at,
        reason=reason,
    )
    return blacklist_entry


async def revoke_all_user_tokens(db: AsyncSession, user_id: UUID, reason: str = "revoked_all") -> int:
    """Revoke all active tokens for a user by adding their JTIs to blacklist.
    Note: This only revokes tokens we know about. For full revocation,
    we'd need to track all issued JTIs per user."""
    # In a production system, you'd maintain a registry of issued tokens per user
    # For now, we return 0 as we don't track all issued JTIs
    return 0


async def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
):
    """FastAPI dependency to get current authenticated user with token revocation check."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
        if payload.type != "access":
            raise ValueError("Invalid token type")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if token is revoked
    if await is_token_revoked(db, payload.jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await db.get(User, UUID(payload.sub))
    if not user or user.deleted_at or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# Re-export for convenience
__all__ = [
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "create_reset_token",
    "decode_token",
    "authenticate_user",
    "get_current_user_dependency",
    "is_token_revoked",
    "revoke_token",
    "revoke_all_user_tokens",
]