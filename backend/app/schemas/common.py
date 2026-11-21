"""Common Pydantic schemas."""
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """Error detail structure."""

    code: str
    message: str
    field: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error response."""

    model_config = ConfigDict(from_attributes=True)

    error: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SuccessResponse(BaseModel):
    """Standard success response."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    message: str
    data: dict[str, Any] | None = None
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """Create paginated response from parameters."""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


class HealthCheckResponse(BaseModel):
    """Health check response."""

    model_config = ConfigDict(from_attributes=True)

    status: str
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: dict[str, Any] = Field(default_factory=dict)


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        str_strip_whitespace=True,
    )


class TimestampMixin(BaseModel):
    """Mixin for created_at/updated_at fields."""

    created_at: datetime
    updated_at: datetime | None = None


class IDMixin(BaseModel):
    """Mixin for ID field."""

    id: UUID