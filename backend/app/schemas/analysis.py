"""Analysis Pydantic schemas."""
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator, field_serializer

from app.config import get_settings

from app.models.analysis import AnalysisStatus, AnalysisType


NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


class AnalysisBase(BaseModel):
    """Base analysis schema."""

    model_config = ConfigDict(from_attributes=True)

    contract_id: UUID
    type: AnalysisType = AnalysisType.FULL
    llm_provider: str = Field(default="openai", max_length=50)
    llm_model: str = Field(default="gpt-4-turbo-preview", max_length=100)
    prompt_version: str = Field(default="1.0", max_length=50)


class AnalysisCreate(AnalysisBase):
    """Analysis creation request using the selected provider's configured model."""

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def configured_provider_and_model(cls, value):
        if not isinstance(value, dict):
            return value
        value = value.copy()
        settings = get_settings()
        provider = value.setdefault("llm_provider", settings.DEFAULT_LLM_PROVIDER)
        model_names = {"openai": "OPENAI_MODEL", "nvidia": "NVIDIA_MODEL", "hermes": "HERMES_MODEL"}
        if provider not in model_names:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        value.setdefault("llm_model", getattr(settings, model_names[provider]))
        return value


class AnalysisUpdate(BaseModel):
    """Analysis update request."""

    model_config = ConfigDict(from_attributes=True)

    status: AnalysisStatus | None = None
    result: dict[str, Any] | None = None
    error_message: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_cost_usd: float | None = None
    processing_time_ms: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AnalysisResponse(AnalysisBase):
    """Analysis response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    created_by_id: UUID
    status: AnalysisStatus
    input_tokens: int | None
    output_tokens: int | None
    total_cost_usd: float | None
    processing_time_ms: int | None
    result: dict[str, Any]
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None

    # Only this separately verified field is trustworthy; result is model data.
    execution_evidence: dict[str, str | None] | None = None

    @model_validator(mode="after")
    def authenticate_execution_evidence(self):
        from app.services.execution_evidence import read_evidence
        self.execution_evidence = read_evidence(self.result, self.id)
        return self

    @field_serializer("result")
    def serialize_result(self, value):
        from app.services.execution_evidence import public_result
        return public_result(value)

    # Computed fields
    contract_title: str | None = None
    clause_count: int = 0
    high_risk_clause_count: int = 0


class AnalysisListResponse(BaseModel):
    """Paginated analysis list response."""

    model_config = ConfigDict(from_attributes=True)

    analyses: list[AnalysisResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class AnalysisResultResponse(BaseModel):
    """Detailed analysis result with clauses and risk summary."""

    model_config = ConfigDict(from_attributes=True)

    analysis: AnalysisResponse
    clauses: list["ClauseSummaryResponse"]
    risk_summary: "RiskSummaryResponse"
    entity_summary: "EntitySummaryResponse"


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


class AnalysisComparisonRequest(BaseModel):
    """Request for comparing two analyses."""

    model_config = ConfigDict(from_attributes=True)

    analysis_id_1: UUID
    analysis_id_2: UUID
    comparison_type: str = Field(default="full", pattern="^(full|clauses|risks|entities)$")


class AnalysisComparisonResponse(BaseModel):
    """Analysis comparison response."""

    model_config = ConfigDict(from_attributes=True)

    analysis_1: AnalysisResponse
    analysis_2: AnalysisResponse
    differences: dict[str, Any]
    similarity_score: float


# Forward references
from app.schemas.clause import ClauseSummaryResponse as _ClauseSummaryResponse
from app.schemas.clause import RiskSummaryResponse as _RiskSummaryResponse
from app.schemas.clause import EntitySummaryResponse as _EntitySummaryResponse

AnalysisResultResponse.model_rebuild()
AnalysisComparisonResponse.model_rebuild()