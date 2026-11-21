"""Test Pydantic schemas."""
import pytest
from uuid import uuid4
from datetime import datetime, timezone

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    Token,
    TokenPayload,
    UserResponse,
)
from app.schemas.contract import (
    ContractCreate,
    ContractResponse,
    ContractStatus,
    ContractSource,
)
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisResponse,
    AnalysisType,
    AnalysisStatus,
)
from app.schemas.clause import (
    ClauseResponse,
    ClauseType,
    RiskLevel,
)
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationPlan,
)
from app.schemas.common import (
    ErrorResponse,
    SuccessResponse,
    PaginatedResponse,
    HealthCheckResponse,
)


def test_login_request_schema():
    """Test LoginRequest schema validation."""
    request = LoginRequest(
        email="test@example.com",
        password="password123",
        remember_me=True,
    )
    assert request.email == "test@example.com"
    assert request.password == "password123"
    assert request.remember_me is True


def test_login_request_invalid_email():
    """Test LoginRequest rejects invalid email."""
    with pytest.raises(ValueError):
        LoginRequest(email="invalid", password="password123")


def test_login_request_short_password():
    """Test LoginRequest rejects short password."""
    with pytest.raises(ValueError):
        LoginRequest(email="test@example.com", password="short")


def test_register_request_schema():
    """Test RegisterRequest schema validation."""
    request = RegisterRequest(
        email="test@example.com",
        password="password123",
        full_name="Test User",
        organization_name="Test Org",
        organization_slug="test-org",
    )
    assert request.email == "test@example.com"
    assert request.organization_slug == "test-org"


def test_token_schema():
    """Test Token schema."""
    token = Token(
        access_token="access-token",
        refresh_token="refresh-token",
        expires_in=1800,
    )
    assert token.token_type == "bearer"
    assert token.expires_in == 1800


def test_token_payload_schema():
    """Test TokenPayload schema."""
    payload = TokenPayload(
        sub=str(uuid4()),
        org_id=str(uuid4()),
        email="test@example.com",
        role="analyst",
        is_superuser=False,
        exp=1234567890,
        iat=1234567890,
    )
    assert payload.type == "access"


def test_contract_create_schema():
    """Test ContractCreate schema."""
    request = ContractCreate(
        title="Test Contract",
        description="A test contract",
        source=ContractSource.UPLOAD,
        language="pt-BR",
    )
    assert request.title == "Test Contract"
    assert request.source == ContractSource.UPLOAD


def test_contract_response_schema():
    """Test ContractResponse schema."""
    response = ContractResponse(
        id=uuid4(),
        organization_id=uuid4(),
        owner_id=uuid4(),
        title="Test Contract",
        status=ContractStatus.UPLOADED,
        source=ContractSource.UPLOAD,
        language="pt-BR",
        meta={},
        file_path=None,
        file_size=None,
        mime_type=None,
        content_hash=None,
        page_count=None,
        error_message=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        deleted_at=None,
    )
    assert response.title == "Test Contract"
    assert response.status == ContractStatus.UPLOADED


def test_analysis_create_schema():
    """Test AnalysisCreate schema."""
    request = AnalysisCreate(
        contract_id=uuid4(),
        type=AnalysisType.FULL,
        llm_provider="openai",
        llm_model="gpt-4-turbo-preview",
    )
    assert request.type == AnalysisType.FULL
    assert request.llm_provider == "openai"


def test_analysis_response_schema():
    """Test AnalysisResponse schema."""
    response = AnalysisResponse(
        id=uuid4(),
        organization_id=uuid4(),
        contract_id=uuid4(),
        created_by_id=uuid4(),
        type=AnalysisType.FULL,
        status=AnalysisStatus.PENDING,
        llm_provider="openai",
        llm_model="gpt-4-turbo-preview",
        prompt_version="1.0",
        result={},
        input_tokens=None,
        output_tokens=None,
        total_cost_usd=None,
        processing_time_ms=None,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        deleted_at=None,
    )
    assert response.type == AnalysisType.FULL
    assert response.status == AnalysisStatus.PENDING


def test_clause_response_schema():
    """Test ClauseResponse schema."""
    response = ClauseResponse(
        id=uuid4(),
        analysis_id=uuid4(),
        contract_id=uuid4(),
        organization_id=uuid4(),
        type=ClauseType.LIABILITY,
        content="Test clause",
        content_hash="abc123",
        risk_score=0.8,
        risk_level=RiskLevel.HIGH,
        risk_factors=["high_value", "unlimited_liability"],
        risk_explanation="High risk due to unlimited liability",
        entities={"parties": ["Company A", "Company B"]},
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        deleted_at=None,
    )
    assert response.type == ClauseType.LIABILITY
    assert response.risk_level == RiskLevel.HIGH


def test_organization_create_schema():
    """Test OrganizationCreate schema."""
    request = OrganizationCreate(
        name="Test Org",
        slug="test-org",
        plan=OrganizationPlan.PRO,
    )
    assert request.name == "Test Org"
    assert request.plan == OrganizationPlan.PRO


def test_organization_response_schema():
    """Test OrganizationResponse schema."""
    response = OrganizationResponse(
        id=uuid4(),
        name="Test Org",
        slug="test-org",
        plan=OrganizationPlan.PRO,
        is_single_tenant=False,
        settings={},
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        deleted_at=None,
    )
    assert response.name == "Test Org"
    assert response.plan == OrganizationPlan.PRO


def test_error_response_schema():
    """Test ErrorResponse schema."""
    error = ErrorResponse(
        error="validation_error",
        message="Invalid input",
        details=[{"code": "INVALID_EMAIL", "message": "Invalid email format"}],
    )
    assert error.error == "validation_error"
    assert len(error.details) == 1


def test_success_response_schema():
    """Test SuccessResponse schema."""
    success = SuccessResponse(message="Operation completed")
    assert success.success is True
    assert success.message == "Operation completed"


def test_paginated_response_schema():
    """Test PaginatedResponse schema."""
    response = PaginatedResponse.create(
        items=[1, 2, 3],
        total=10,
        page=1,
        page_size=3,
    )
    assert response.total == 10
    assert response.page == 1
    assert response.page_size == 3
    assert response.total_pages == 4
    assert response.has_next is True
    assert response.has_prev is False


def test_health_check_response_schema():
    """Test HealthCheckResponse schema."""
    response = HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        environment="development",
    )
    assert response.status == "healthy"
    assert response.version == "1.0.0"