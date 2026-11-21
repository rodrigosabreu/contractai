"""Analysis model."""
import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, String, Text, func, Index
from sqlalchemy import ForeignKey, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnalysisStatus(str, enum.Enum):
    """Analysis processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisType(str, enum.Enum):
    """Type of analysis performed."""

    FULL = "full"
    CLAUSE_EXTRACTION = "clause_extraction"
    RISK_ASSESSMENT = "risk_assessment"
    COMPARISON = "comparison"
    ENTITY_EXTRACTION = "entity_extraction"


class Analysis(Base):
    """Contract analysis model."""

    __tablename__ = "analyses"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    contract_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("contracts.id"), nullable=False, index=True
    )
    created_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    type: Mapped[AnalysisType] = mapped_column(
        Enum(AnalysisType), default=AnalysisType.FULL, nullable=False
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False, index=True
    )
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    total_cost_usd: Mapped[float | None] = mapped_column(nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(nullable=True)
    result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="analyses")
    contract: Mapped["Contract"] = relationship(back_populates="analyses")
    created_by_user: Mapped["User"] = relationship(back_populates="analyses")
    clauses: Mapped[list["Clause"]] = relationship(back_populates="analysis", lazy="selectin")

    __table_args__ = (
        Index("ix_analyses_org_status", "organization_id", "status"),
        Index("ix_analyses_contract_type", "contract_id", "type"),
    )

    def __repr__(self) -> str:
        return f"<Analysis(id={self.id}, contract_id={self.contract_id}, status={self.status})>"