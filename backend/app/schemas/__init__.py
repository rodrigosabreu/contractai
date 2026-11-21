"""Pydantic schemas package."""
from app.schemas.auth import (
    Token,
    TokenPayload,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    PasswordChangeRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    MFAEnableRequest,
    MFAVerifyRequest,
)
from app.schemas.contract import (
    ContractCreate,
    ContractUpdate,
    ContractResponse,
    ContractListResponse,
    ContractVersionResponse,
    ContractUploadResponse,
)
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisResponse,
    AnalysisListResponse,
    AnalysisResultResponse,
)
from app.schemas.clause import (
    ClauseResponse,
    ClauseListResponse,
    ClauseSearchRequest,
    ClauseSearchResponse,
)
from app.schemas.connector import (
    ConnectorCreate,
    ConnectorUpdate,
    ConnectorResponse,
    ConnectorListResponse,
    ConnectorSyncRequest,
    ConnectorSyncResponse,
    GoogleDriveAuthRequest,
    GoogleDriveAuthResponse,
    OneDriveAuthRequest,
    OneDriveAuthResponse,
)
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationListResponse,
    OrganizationSettingsUpdate,
    UserInviteRequest,
    UserInviteResponse,
)
from app.schemas.common import (
    PaginatedResponse,
    ErrorResponse,
    SuccessResponse,
    HealthCheckResponse,
)

__all__ = [
    # Auth
    "Token",
    "TokenPayload",
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "RegisterRequest",
    "RegisterResponse",
    "PasswordChangeRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "MFAEnableRequest",
    "MFAVerifyRequest",
    # Contract
    "ContractCreate",
    "ContractUpdate",
    "ContractResponse",
    "ContractListResponse",
    "ContractVersionResponse",
    "ContractUploadResponse",
    # Analysis
    "AnalysisCreate",
    "AnalysisResponse",
    "AnalysisListResponse",
    "AnalysisResultResponse",
    # Clause
    "ClauseResponse",
    "ClauseListResponse",
    "ClauseSearchRequest",
    "ClauseSearchResponse",
    # Connector
    "ConnectorCreate",
    "ConnectorUpdate",
    "ConnectorResponse",
    "ConnectorListResponse",
    "ConnectorSyncRequest",
    "ConnectorSyncResponse",
    "GoogleDriveAuthRequest",
    "GoogleDriveAuthResponse",
    "OneDriveAuthRequest",
    "OneDriveAuthResponse",
    # Organization
    "OrganizationCreate",
    "OrganizationUpdate",
    "OrganizationResponse",
    "OrganizationListResponse",
    "OrganizationSettingsUpdate",
    "UserInviteRequest",
    "UserInviteResponse",
    # Common
    "PaginatedResponse",
    "ErrorResponse",
    "SuccessResponse",
    "HealthCheckResponse",
]