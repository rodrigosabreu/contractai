"""Clause Pydantic schemas."""
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.clause import ClauseType, RiskLevel


NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


class ClauseBase(BaseModel):
    """Base clause schema."""

    model_config = ConfigDict(from_attributes=True)

    clause_number: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, max_length=500)
    type: ClauseType = ClauseType.GENERAL
    content: str
    page_start: int | None = None
    page_end: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    language: str = Field(default="pt-BR", max_length=10)
    meta: dict[str, Any] = Field(default_factory=dict)


class ClauseCreate(ClauseBase):
    """Clause creation request (internal use)."""

    model_config = ConfigDict(from_attributes=True)

    analysis_id: UUID
    contract_id: UUID
    organization_id: UUID
    content_hash: str = Field(max_length=64)
    embedding: list[float] | None = None
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_level: RiskLevel = RiskLevel.LOW
    risk_factors: list[str] = Field(default_factory=list)
    risk_explanation: str | None = None
    entities: dict[str, Any] = Field(default_factory=dict)


class ClauseUpdate(BaseModel):
    """Clause update request."""

    model_config = ConfigDict(from_attributes=True)

    clause_number: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, max_length=500)
    type: ClauseType | None = None
    risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    risk_level: RiskLevel | None = None
    risk_factors: list[str] | None = None
    risk_explanation: str | None = None
    entities: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


class ClauseResponse(ClauseBase):
    """Clause response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_id: UUID
    contract_id: UUID
    organization_id: UUID
    content_hash: str
    embedding: list[float] | None = None
    risk_score: float
    risk_level: RiskLevel
    risk_factors: list[str]
    risk_explanation: str | None
    entities: dict[str, Any]
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None

    # Computed fields
    has_embedding: bool = False
    is_high_risk: bool = False


class ClauseListResponse(BaseModel):
    """Paginated clause list response."""

    model_config = ConfigDict(from_attributes=True)

    clauses: list[ClauseResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ClauseSearchRequest(BaseModel):
    """Clause semantic search request."""

    model_config = ConfigDict(from_attributes=True)

    query: NonEmptyStr = Field(max_length=1000)
    organization_id: UUID
    contract_id: UUID | None = None
    analysis_id: UUID | None = None
    clause_types: list[ClauseType] | None = None
    risk_levels: list[RiskLevel] | None = None
    min_risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    max_risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class ClauseSearchResult(BaseModel):
    """Single clause search result with similarity score."""

    model_config = ConfigDict(from_attributes=True)

    clause: ClauseResponse
    similarity_score: float


class ClauseSearchResponse(BaseModel):
    """Clause search response with results."""

    model_config = ConfigDict(from_attributes=True)

    results: list[ClauseSearchResult]
    total: int
    query: str
    took_ms: int


class ClauseSummaryResponse(BaseModel):
    """Clause summary for analysis results."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clause_number: str | None
    title: str | None
    type: str
    risk_level: str
    risk_score: float
    page_start: int | None
    page_end: int | None


class RiskSummaryResponse(BaseModel):
    """Risk assessment summary."""

    model_config = ConfigDict(from_attributes=True)

    overall_risk_score: float | None = None
    overall_risk_level: str | None = None
    overall_risk_level_source: str | None = None
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    risk_factors: list[str]


class EntitySummaryResponse(BaseModel):
    """Extracted entities summary."""

    model_config = ConfigDict(from_attributes=True)

    parties: list[dict[str, Any]]
    dates: list[dict[str, Any]]
    amounts: list[dict[str, Any]]
    references: list[dict[str, Any]]


class ClauseBulkRiskUpdate(BaseModel):
    """Bulk risk level update for clauses."""

    model_config = ConfigDict(from_attributes=True)

    clause_ids: list[UUID]
    risk_level: RiskLevel
    risk_explanation: str | None = None