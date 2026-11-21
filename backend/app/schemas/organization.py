"""Organization Pydantic schemas."""
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.models.organization import OrganizationPlan


class OrganizationBase(BaseModel):
    """Base organization schema."""

    model_config = ConfigDict(from_attributes=True)

    name: Annotated[str, StringConstraints(min_length=1, max_length=255, strip_whitespace=True)]
    slug: Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]+$", min_length=3, max_length=100)]


class OrganizationCreate(OrganizationBase):
    """Organization creation request."""

    model_config = ConfigDict(from_attributes=True)

    plan: OrganizationPlan = OrganizationPlan.FREE
    settings: dict[str, Any] = Field(default_factory=dict)


class OrganizationUpdate(BaseModel):
    """Organization update request."""

    model_config = ConfigDict(from_attributes=True)

    name: Annotated[str | None, StringConstraints(min_length=1, max_length=255, strip_whitespace=True)] = None
    plan: OrganizationPlan | None = None
    settings: dict[str, Any] | None = None
    is_single_tenant: bool | None = None


class OrganizationSettingsUpdate(BaseModel):
    """Organization settings update request."""

    model_config = ConfigDict(from_attributes=True)

    settings: dict[str, Any]


class OrganizationResponse(OrganizationBase):
    """Organization response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan: OrganizationPlan
    is_single_tenant: bool
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None

    # Computed fields
    user_count: int = 0
    contract_count: int = 0
    analysis_count: int = 0
    storage_used_mb: float = 0.0


class OrganizationListResponse(BaseModel):
    """Paginated organization list response."""

    model_config = ConfigDict(from_attributes=True)

    organizations: list[OrganizationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class UserInviteRequest(BaseModel):
    """User invitation request."""

    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    role: Annotated[str, StringConstraints(pattern=r"^(admin|manager|analyst|viewer)$")] = "viewer"
    message: str | None = None


class UserInviteResponse(BaseModel):
    """User invitation response."""

    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    role: str
    invited_by: str
    expires_at: datetime
    invite_token: str


class OrganizationStatsResponse(BaseModel):
    """Organization statistics response."""

    model_config = ConfigDict(from_attributes=True)

    total_users: int
    active_users: int
    total_contracts: int
    contracts_this_month: int
    total_analyses: int
    analyses_this_month: int
    storage_used_mb: float
    storage_limit_mb: float | None = None
    plan: OrganizationPlan
    connectors: dict[str, int] = Field(default_factory=dict)


class OrganizationPlanLimits(BaseModel):
    """Plan limits configuration."""

    model_config = ConfigDict(from_attributes=True)

    max_users: int | None = None
    max_contracts_per_month: int | None = None
    max_analyses_per_month: int | None = None
    max_storage_mb: int | None = None
    max_file_size_mb: int
    allowed_connectors: list[str]
    api_access: bool
    custom_branding: bool
    sso_enabled: bool
    audit_log_retention_days: int
    data_retention_days: int


PLAN_LIMITS: dict[OrganizationPlan, OrganizationPlanLimits] = {
    OrganizationPlan.FREE: OrganizationPlanLimits(
        max_users=5,
        max_contracts_per_month=10,
        max_analyses_per_month=20,
        max_storage_mb=100,
        max_file_size_mb=10,
        allowed_connectors=[],
        api_access=False,
        custom_branding=False,
        sso_enabled=False,
        audit_log_retention_days=30,
        data_retention_days=90,
    ),
    OrganizationPlan.PRO: OrganizationPlanLimits(
        max_users=25,
        max_contracts_per_month=100,
        max_analyses_per_month=200,
        max_storage_mb=5000,
        max_file_size_mb=50,
        allowed_connectors=["google_drive"],
        api_access=True,
        custom_branding=False,
        sso_enabled=False,
        audit_log_retention_days=365,
        data_retention_days=2555,
    ),
    OrganizationPlan.ENTERPRISE: OrganizationPlanLimits(
        max_users=None,
        max_contracts_per_month=None,
        max_analyses_per_month=None,
        max_storage_mb=None,
        max_file_size_mb=200,
        allowed_connectors=["google_drive", "onedrive"],
        api_access=True,
        custom_branding=True,
        sso_enabled=True,
        audit_log_retention_days=2555,
        data_retention_days=2555,
    ),
}


def get_plan_limits(plan: OrganizationPlan) -> OrganizationPlanLimits:
    """Get limits for a specific plan."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[OrganizationPlan.FREE])