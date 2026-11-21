"""Clause model with risk scoring (SQLite compatible)."""
import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Float, String, Text, func, Index
from sqlalchemy import ForeignKey, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClauseType(str, enum.Enum):
    """Types of contract clauses."""

    PARTIES = "parties"
    DEFINITIONS = "definitions"
    SCOPE = "scope"
    OBLIGATIONS = "obligations"
    PAYMENT = "payment"
    TERM = "term"
    TERMINATION = "termination"
    LIABILITY = "liability"
    INDEMNIFICATION = "indemnification"
    CONFIDENTIALITY = "confidentiality"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    DISPUTE_RESOLUTION = "dispute_resolution"
    FORCE_MAJEURE = "force_majeure"
    GOVERNING_LAW = "governing_law"
    AMENDMENT = "amendment"
    ASSIGNMENT = "assignment"
    NOTICES = "notices"
    GENERAL = "general"
    OTHER = "other"


class RiskLevel(str, enum.Enum):
    """Risk level classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Clause(Base):
    """Contract clause with risk scoring (SQLite compatible)."""

    __tablename__ = "clauses"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    analysis_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analyses.id"), nullable=False, index=True
    )
    contract_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("contracts.id"), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )

    # Clause identification
    clause_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    type: Mapped[ClauseType] = mapped_column(
        Enum(ClauseType), default=ClauseType.GENERAL, nullable=False, index=True
    )

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Position in document
    page_start: Mapped[int | None] = mapped_column(nullable=True)
    page_end: Mapped[int | None] = mapped_column(nullable=True)
    char_start: Mapped[int | None] = mapped_column(nullable=True)
    char_end: Mapped[int | None] = mapped_column(nullable=True)

    # Vector embedding (stored as JSON text for SQLite compatibility)
    # TODO: Enable when pgvector is available
    # embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON text

    # Risk assessment
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel), default=RiskLevel.LOW, nullable=False, index=True
    )
    risk_factors: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    risk_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extracted entities
    entities: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Metadata
    language: Mapped[str] = mapped_column(String(10), default="pt-BR", nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    analysis: Mapped["Analysis"] = relationship(back_populates="clauses")

    __table_args__ = (
        Index("ix_clauses_analysis_type", "analysis_id", "type"),
        Index("ix_clauses_org_risk", "organization_id", "risk_level"),
        Index("ix_clauses_contract_risk", "contract_id", "risk_score"),
        # Vector similarity search index (disabled for SQLite)
        # Index("ix_clauses_embedding", "embedding", postgresql_using="ivfflat", postgresql_with={"lists": 100}),
    )

    def __repr__(self) -> str:
        return f"<Clause(id={self.id}, type={self.type}, risk={self.risk_level})>"

    @property
    def is_high_risk(self) -> bool:
        """Check if clause is high or critical risk."""
        return self.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    @property
    def has_embedding(self) -> bool:
        """Check if clause has vector embedding."""
        return self.embedding is not None and len(self.embedding) > 0