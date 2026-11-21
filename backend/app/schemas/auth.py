"""Authentication Pydantic schemas."""
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.models.user import UserRole


# Constrained strings
NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
PasswordStr = Annotated[str, StringConstraints(min_length=8, max_length=128)]
RoleStr = Annotated[str, StringConstraints(pattern=r"^(admin|manager|analyst|viewer)$")]


class Token(BaseModel):
    """JWT token response."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenPayload(BaseModel):
    """JWT token payload."""

    model_config = ConfigDict(from_attributes=True)

    sub: str  # user_id
    org_id: str  # organization_id
    email: str
    role: UserRole
    is_superuser: bool = False
    exp: int
    iat: int
    type: str = "access"  # access or refresh
    jti: str | None = None  # JWT ID for revocation


class LoginRequest(BaseModel):
    """Login request."""

    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    password: PasswordStr
    remember_me: bool = False


class LoginResponse(BaseModel):
    """Login response with user info."""

    model_config = ConfigDict(from_attributes=True)

    user: "UserResponse"
    tokens: Token


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    model_config = ConfigDict(from_attributes=True)

    refresh_token: str


class RegisterRequest(BaseModel):
    """User registration request."""

    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    password: PasswordStr
    full_name: NonEmptyStr = Field(max_length=255)
    organization_name: NonEmptyStr = Field(max_length=255)
    organization_slug: Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]+$", min_length=3, max_length=100)]


class RegisterResponse(BaseModel):
    """User registration response."""

    model_config = ConfigDict(from_attributes=True)

    user: "UserResponse"
    organization: "OrganizationResponse"
    tokens: Token


class PasswordChangeRequest(BaseModel):
    """Password change request."""

    model_config = ConfigDict(from_attributes=True)

    current_password: PasswordStr
    new_password: PasswordStr


class PasswordResetRequest(BaseModel):
    """Password reset request (forgot password)."""

    model_config = ConfigDict(from_attributes=True)

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""

    model_config = ConfigDict(from_attributes=True)

    token: str
    new_password: PasswordStr


class MFAEnableRequest(BaseModel):
    """MFA enable request."""

    model_config = ConfigDict(from_attributes=True)

    code: Annotated[str, StringConstraints(pattern=r"^\d{6}$")]


class MFAVerifyRequest(BaseModel):
    """MFA verify request."""

    model_config = ConfigDict(from_attributes=True)

    code: Annotated[str, StringConstraints(pattern=r"^\d{6}$")]
    backup_code: str | None = None


class UserResponse(BaseModel):
    """User response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    is_superuser: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime | None


class UserUpdateRequest(BaseModel):
    """User update request."""

    model_config = ConfigDict(from_attributes=True)

    full_name: NonEmptyStr | None = Field(default=None, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None


class UserInviteRequest(BaseModel):
    """User invite request."""

    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    role: UserRole = UserRole.VIEWER
    message: str | None = None


class UserInviteResponse(BaseModel):
    """User invite response."""

    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    role: UserRole
    invited_by: str
    expires_at: datetime


# Forward references
from app.schemas.organization import OrganizationResponse  # noqa: E402

LoginResponse.model_rebuild()
RegisterResponse.model_rebuild()