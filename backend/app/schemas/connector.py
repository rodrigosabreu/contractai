"""Connector Pydantic schemas."""
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class ConnectorBase(BaseModel):
    """Base connector schema."""

    model_config = ConfigDict(from_attributes=True)

    name: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)]
    type: Annotated[str, StringConstraints(pattern=r"^(google_drive|onedrive)$")]
    config: dict[str, Any] = Field(default_factory=dict)


class ConnectorCreate(ConnectorBase):
    """Connector creation request."""

    model_config = ConfigDict(from_attributes=True)

    credentials: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class ConnectorUpdate(BaseModel):
    """Connector update request."""

    model_config = ConfigDict(from_attributes=True)

    name: Annotated[str | None, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = None
    config: dict[str, Any] | None = None
    credentials: dict[str, Any] | None = None
    is_active: bool | None = None


class ConnectorResponse(ConnectorBase):
    """Connector response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    is_active: bool
    last_sync_at: datetime | None
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None


class ConnectorListResponse(BaseModel):
    """Paginated connector list response."""

    model_config = ConfigDict(from_attributes=True)

    connectors: list[ConnectorResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ConnectorSyncRequest(BaseModel):
    """Connector sync request."""

    model_config = ConfigDict(from_attributes=True)

    full_sync: bool = False
    folder_id: str | None = None
    file_types: list[str] | None = None


class ConnectorSyncResponse(BaseModel):
    """Connector sync response."""

    model_config = ConfigDict(from_attributes=True)

    sync_id: UUID
    status: str
    files_found: int = 0
    files_synced: int = 0
    files_failed: int = 0
    errors: list[str] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None


class GoogleDriveAuthRequest(BaseModel):
    """Google Drive OAuth authorization request."""

    model_config = ConfigDict(from_attributes=True)

    redirect_uri: str | None = None
    state: str | None = None


class GoogleDriveAuthResponse(BaseModel):
    """Google Drive OAuth authorization response."""

    model_config = ConfigDict(from_attributes=True)

    auth_url: str
    state: str


class OneDriveAuthRequest(BaseModel):
    """OneDrive OAuth authorization request."""

    model_config = ConfigDict(from_attributes=True)

    redirect_uri: str | None = None
    state: str | None = None


class OneDriveAuthResponse(BaseModel):
    """OneDrive OAuth authorization response."""

    model_config = ConfigDict(from_attributes=True)

    auth_url: str
    state: str


class ConnectorCallbackRequest(BaseModel):
    """OAuth callback request."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    state: str
    error: str | None = None
    error_description: str | None = None


class ConnectorCallbackResponse(BaseModel):
    """OAuth callback response."""

    model_config = ConfigDict(from_attributes=True)

    success: bool
    connector: ConnectorResponse | None = None
    message: str