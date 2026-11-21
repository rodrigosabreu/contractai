"""AuditLog model for LGPD compliance and security auditing."""
import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, String, Text, func, Index
from sqlalchemy import ForeignKey, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AuditAction(str, enum.Enum):
    """Types of auditable actions."""

    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_COMPLETE = "password_reset_complete"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKED = "token_revoked"

    # User management
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_RESTORE = "user_restore"
    USER_ROLE_CHANGE = "user_role_change"
    USER_ACTIVATE = "user_activate"
    USER_DEACTIVATE = "user_deactivate"

    # Organization
    ORG_CREATE = "org_create"
    ORG_UPDATE = "org_update"
    ORG_DELETE = "org_delete"
    ORG_SETTINGS_CHANGE = "org_settings_change"
    ORG_PLAN_CHANGE = "org_plan_change"

    # Contracts
    CONTRACT_UPLOAD = "contract_upload"
    CONTRACT_DOWNLOAD = "contract_download"
    CONTRACT_VIEW = "contract_view"
    CONTRACT_UPDATE = "contract_update"
    CONTRACT_DELETE = "contract_delete"
    CONTRACT_RESTORE = "contract_restore"
    CONTRACT_VERSION_CREATE = "contract_version_create"
    CONTRACT_SHARE = "contract_share"
    CONTRACT_EXPORT = "contract_export"

    # Analysis
    ANALYSIS_START = "analysis_start"
    ANALYSIS_COMPLETE = "analysis_complete"
    ANALYSIS_FAILED = "analysis_failed"
    ANALYSIS_VIEW = "analysis_view"
    ANALYSIS_EXPORT = "analysis_export"
    ANALYSIS_DELETE = "analysis_delete"

    # Clauses
    CLAUSE_VIEW = "clause_view"
    CLAUSE_EXPORT = "clause_export"

    # Connectors
    CONNECTOR_CREATE = "connector_create"
    CONNECTOR_UPDATE = "connector_update"
    CONNECTOR_DELETE = "connector_delete"
    CONNECTOR_SYNC = "connector_sync"
    CONNECTOR_AUTH = "connector_auth"

    # Data privacy (LGPD)
    DATA_EXPORT_REQUEST = "data_export_request"
    DATA_EXPORT_COMPLETE = "data_export_complete"
    DATA_DELETION_REQUEST = "data_deletion_request"
    DATA_DELETION_COMPLETE = "data_deletion_complete"
    DATA_ANONYMIZE = "data_anonymize"
    CONSENT_GIVEN = "consent_given"
    CONSENT_WITHDRAWN = "consent_withdrawn"

    # System
    SETTINGS_CHANGE = "settings_change"
    BACKUP_CREATE = "backup_create"
    BACKUP_RESTORE = "backup_restore"


class AuditStatus(str, enum.Enum):
    """Audit log entry status."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class AuditLog(Base):
    """Audit log for compliance and security monitoring (LGPD Art. 10)."""

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )

    # Action details
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction), nullable=False, index=True
    )
    status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus), default=AuditStatus.SUCCESS, nullable=False, index=True
    )

    # Resource affected
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Details
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # LGPD specific fields
    data_subject_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    legal_basis: Mapped[str | None] = mapped_column(String(100), nullable=True)
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="audit_logs")
    user: Mapped["User | None"] = relationship(back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_org_action", "organization_id", "action"),
        Index("ix_audit_logs_org_created", "organization_id", "created_at"),
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_data_subject", "data_subject_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, status={self.status})>"

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        action: AuditAction,
        user_id: UUID | None = None,
        status: AuditStatus = AuditStatus.SUCCESS,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        session_id: str | None = None,
        details: dict | None = None,
        error_message: str | None = None,
        data_subject_id: str | None = None,
        legal_basis: str | None = None,
        retention_days: int | None = None,
    ) -> "AuditLog":
        """Factory method to create an audit log entry."""
        from app.config import get_settings

        settings = get_settings()
        retention_until = None
        if retention_days is not None:
            from datetime import timedelta

            retention_until = datetime.utcnow() + timedelta(days=retention_days)
        elif settings.AUDIT_LOG_RETENTION_DAYS:
            from datetime import timedelta

            retention_until = datetime.utcnow() + timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)

        return cls(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            status=status,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            session_id=session_id,
            details=details or {},
            error_message=error_message,
            data_subject_id=data_subject_id,
            legal_basis=legal_basis,
            retention_until=retention_until,
        )