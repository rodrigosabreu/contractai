"""Contract Pydantic schemas."""
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.analysis import AnalysisStatus
from app.models.contract import ContractSource, ContractStatus


NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


class ContractBase(BaseModel):
    """Base contract schema."""

    model_config = ConfigDict(from_attributes=True)

    title: NonEmptyStr = Field(max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    source: ContractSource = ContractSource.UPLOAD
    source_id: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=1000)
    language: str = Field(default="pt-BR", max_length=10)


class ContractCreate(ContractBase):
    """Contract creation request."""

    model_config = ConfigDict(from_attributes=True)

    file_content: str | None = None  # base64 encoded
    file_name: str | None = None
    mime_type: str | None = Field(default=None, max_length=100)


class ContractUpdate(BaseModel):
    """Contract update request."""

    model_config = ConfigDict(from_attributes=True)

    title: NonEmptyStr | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    language: str | None = Field(default=None, max_length=10)
    meta: dict | None = None


class ContractResponse(ContractBase):
    """Contract response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    owner_id: UUID
    status: ContractStatus
    file_path: str | None
    file_size: int | None
    mime_type: str | None
    content_hash: str | None
    page_count: int | None
    meta: dict
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    # Computed fields
    analysis_count: int = 0
    latest_analysis_status: AnalysisStatus | None = None


class ContractListResponse(BaseModel):
    """Paginated contract list response."""

    model_config = ConfigDict(from_attributes=True)

    contracts: list[ContractResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ContractVersionResponse(BaseModel):
    """Contract version response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contract_id: UUID
    version_number: int
    content_hash: str
    change_summary: str | None
    created_by_id: UUID
    created_at: datetime


class ContractUploadResponse(BaseModel):
    """Contract upload response."""

    model_config = ConfigDict(from_attributes=True)

    contract: ContractResponse
    upload_id: str
    status: ContractStatus
    message: str