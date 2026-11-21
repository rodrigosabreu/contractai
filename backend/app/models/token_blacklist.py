"""Token blacklist model for JWT revocation."""
import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, String, func, Index
from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TokenType(str, enum.Enum):
    """Token types for blacklisting."""

    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"


class RevocationReason(str, enum.Enum):
    """Reasons for token revocation."""

    LOGOUT = "logout"
    REFRESH = "refresh"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    USER_DEACTIVATED = "user_deactivated"
    USER_DELETED = "user_deleted"
    ADMIN_REVOKE = "admin_revoke"
    SECURITY_INCIDENT = "security_incident"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"


class TokenBlacklist(Base):
    """Blacklisted JWT tokens (by JTI)."""

    __tablename__ = "token_blacklist"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    token_type: Mapped[TokenType] = mapped_column(
        Enum(TokenType), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(50), nullable=False, default="revoked")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_token_blacklist_expires_at", "expires_at"),
        Index("ix_token_blacklist_user_id_type", "user_id", "token_type"),
    )

    def __repr__(self) -> str:
        return f"<TokenBlacklist(jti={self.jti}, type={self.token_type}, user={self.user_id})>"