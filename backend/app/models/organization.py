"""Organization model."""
import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy import ForeignKey, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrganizationPlan(str, enum.Enum):
    """Organization subscription plans."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Organization(Base):
    """Organization model for multi-tenancy."""

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    plan: Mapped[OrganizationPlan] = mapped_column(
        Enum(OrganizationPlan), default=OrganizationPlan.FREE, nullable=False
    )
    is_single_tenant: Mapped[bool] = mapped_column(default=False, nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="organization", lazy="selectin")
    contracts: Mapped[list["Contract"]] = relationship(back_populates="organization", lazy="selectin")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="organization", lazy="selectin")
    connectors: Mapped[list["Connector"]] = relationship(back_populates="organization", lazy="selectin")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="organization", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name}, plan={self.plan})>"


class Connector(Base):
    """External storage connector configuration."""

    __tablename__ = "connectors"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # google_drive, onedrive
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    credentials: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="connectors")

    def __repr__(self) -> str:
        return f"<Connector(id={self.id}, type={self.type}, name={self.name})>"