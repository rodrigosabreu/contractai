"""Contract model."""
import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, String, Text, func, Index
from sqlalchemy import ForeignKey, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ContractStatus(str, enum.Enum):
    """Contract processing status."""

    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    ERROR = "error"


class ContractSource(str, enum.Enum):
    """Contract source type."""

    UPLOAD = "upload"
    GOOGLE_DRIVE = "google_drive"
    ONEDRIVE = "onedrive"
    API = "api"


class Contract(Base):
    """Contract document model."""

    __tablename__ = "contracts"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    owner_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[ContractSource] = mapped_column(
        Enum(ContractSource), default=ContractSource.UPLOAD, nullable=False
    )
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_size: Mapped[int | None] = mapped_column(nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus), default=ContractStatus.UPLOADED, nullable=False, index=True
    )
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    page_count: Mapped[int | None] = mapped_column(nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="pt-BR", nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="contracts")
    owner: Mapped["User"] = relationship(back_populates="contracts")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="contract", lazy="selectin")
    versions: Mapped[list["ContractVersion"]] = relationship(back_populates="contract", lazy="selectin")

    __table_args__ = (
        Index("ix_contracts_org_status", "organization_id", "status"),
        Index("ix_contracts_org_created", "organization_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Contract(id={self.id}, title={self.title}, status={self.status})>"


class ContractVersion(Base):
    """Contract version for diff/comparison."""

    __tablename__ = "contract_versions"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    contract_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("contracts.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    contract: Mapped["Contract"] = relationship(back_populates="versions")

    __table_args__ = (
        Index("ix_contract_versions_contract_version", "contract_id", "version_number", unique=True),
    )

    def __repr__(self) -> str:
        return f"<ContractVersion(contract_id={self.contract_id}, version={self.version_number})>"