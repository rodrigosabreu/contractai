"""Test database models."""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone

# Import models after app is configured
from app.models.user import User, UserRole
from app.models.organization import Organization, OrganizationPlan
from app.models.contract import Contract, ContractSource, ContractStatus
from app.models.analysis import Analysis, AnalysisType, AnalysisStatus
from app.models.clause import Clause, ClauseType, RiskLevel
from app.models.audit_log import AuditLog, AuditAction, AuditStatus
from app.models.token_blacklist import TokenBlacklist, TokenType, RevocationReason
from app.database import Base


@pytest.fixture
def session():
    """Exercise insert defaults in a private SQLite database."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_user_model(session):
    """Test User model creation."""
    org = Organization(id=uuid4(), name="Fiction", slug="fiction")
    session.add(org)
    session.flush()
    user = User(
        id=uuid4(),
        organization_id=org.id,
        email="test@example.com",
        hashed_password="hashed",
        full_name="Test User",
        role=UserRole.ANALYST,
    )
    session.add(user)
    session.flush()
    session.expire(user)
    assert user.email == "test@example.com"
    assert user.role == UserRole.ANALYST
    assert user.is_active is True
    assert user.is_superuser is False


def test_organization_model(session):
    """Test Organization model creation."""
    org = Organization(
        id=uuid4(),
        name="Test Org",
        slug="test-org",
        plan=OrganizationPlan.PRO,
    )
    session.add(org)
    session.flush()
    session.expire(org)
    assert org.name == "Test Org"
    assert org.slug == "test-org"
    assert org.plan == OrganizationPlan.PRO
    assert org.is_single_tenant is False


def test_contract_model():
    """Test Contract model creation."""
    contract = Contract(
        id=uuid4(),
        organization_id=uuid4(),
        owner_id=uuid4(),
        title="Test Contract",
        source=ContractSource.UPLOAD,
        status=ContractStatus.UPLOADED,
    )
    assert contract.title == "Test Contract"
    assert contract.source == ContractSource.UPLOAD
    assert contract.status == ContractStatus.UPLOADED


def test_analysis_model():
    """Test Analysis model creation."""
    analysis = Analysis(
        id=uuid4(),
        organization_id=uuid4(),
        contract_id=uuid4(),
        created_by_id=uuid4(),
        type=AnalysisType.FULL,
        status=AnalysisStatus.PENDING,
        llm_provider="openai",
        llm_model="gpt-4-turbo-preview",
        prompt_version="1.0",
    )
    assert analysis.type == AnalysisType.FULL
    assert analysis.status == AnalysisStatus.PENDING


def test_clause_model():
    """Test Clause model creation."""
    clause = Clause(
        id=uuid4(),
        analysis_id=uuid4(),
        contract_id=uuid4(),
        organization_id=uuid4(),
        type=ClauseType.LIABILITY,
        content="Test clause content",
        content_hash="abc123",
        risk_score=0.8,
        risk_level=RiskLevel.HIGH,
    )
    assert clause.type == ClauseType.LIABILITY
    assert clause.risk_score == 0.8
    assert clause.risk_level == RiskLevel.HIGH


def test_audit_log_model():
    """Test AuditLog model creation."""
    audit = AuditLog(
        id=uuid4(),
        organization_id=uuid4(),
        user_id=uuid4(),
        action=AuditAction.LOGIN,
        status=AuditStatus.SUCCESS,
    )
    assert audit.action == AuditAction.LOGIN
    assert audit.status == AuditStatus.SUCCESS


def test_token_blacklist_model():
    """Test TokenBlacklist model creation."""
    blacklist = TokenBlacklist(
        id=uuid4(),
        jti="test-jti",
        token_type="access",
        user_id=uuid4(),
        expires_at=datetime.now(timezone.utc),
        reason="logout",
    )
    assert blacklist.jti == "test-jti"
    assert blacklist.token_type == "access"
    assert blacklist.reason == "logout"


def test_user_role_enum():
    """Test UserRole enum values."""
    assert UserRole.ADMIN.value == "admin"
    assert UserRole.MANAGER.value == "manager"
    assert UserRole.ANALYST.value == "analyst"
    assert UserRole.VIEWER.value == "viewer"


def test_organization_plan_enum():
    """Test OrganizationPlan enum values."""
    assert OrganizationPlan.FREE.value == "free"
    assert OrganizationPlan.PRO.value == "pro"
    assert OrganizationPlan.ENTERPRISE.value == "enterprise"


def test_contract_status_enum():
    """Test ContractStatus enum values."""
    assert ContractStatus.UPLOADED.value == "uploaded"
    assert ContractStatus.PARSING.value == "parsing"
    assert ContractStatus.ANALYZED.value == "analyzed"
    assert ContractStatus.ERROR.value == "error"


def test_risk_level_enum():
    """Test RiskLevel enum values."""
    assert RiskLevel.LOW.value == "low"
    assert RiskLevel.MEDIUM.value == "medium"
    assert RiskLevel.HIGH.value == "high"
    assert RiskLevel.CRITICAL.value == "critical"