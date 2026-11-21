"""Integration tests for the analysis task using real SQLite ORM models."""
import asyncio
import hashlib
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models.organization import Organization
from app.models.user import User
from app.models.contract import Contract
from app.models.analysis import Analysis, AnalysisStatus
from app.models.clause import Clause, ClauseType, RiskLevel
from app.workers import tasks


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def db(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'worker.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as session:
            org = Organization(name="Tenant A", slug="a")
            other = Organization(name="Tenant B", slug="b")
            session.add_all([org, other]); await session.flush()
            user = User(organization_id=org.id, email="test@example.test", hashed_password="x", full_name="Test")
            session.add(user); await session.flush()
            contract = Contract(organization_id=org.id, owner_id=user.id, title="Synthetic", content_text="Synthetic text")
            session.add(contract); await session.flush()
            analysis = Analysis(organization_id=org.id, contract_id=contract.id, created_by_id=user.id, llm_provider="test", llm_model="test", prompt_version="1")
            session.add(analysis); await session.commit()
            return analysis.id, other.id, contract.id
    ids = run(setup())
    @asynccontextmanager
    async def context():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    monkeypatch.setattr(tasks, "get_db_context", context)
    yield factory, ids
    run(engine.dispose())


def test_real_sqlite_success_maps_clause_and_timing(db, monkeypatch):
    factory, (analysis_id, _, _) = db
    class Service:
        def __init__(self, _): pass
        async def analyze_contract(self, **kwargs):
            return {"clauses": [{"number": "1", "type": "payment", "content": "Pay.", "risk_level": "high"}]}
    monkeypatch.setattr(tasks, "get_llm_client", lambda: object())
    monkeypatch.setattr("app.services.analysis.AnalysisService", Service)
    monkeypatch.setattr(tasks, "AnalysisService", Service)
    result = tasks.analyze_contract.apply(args=[str(analysis_id)], throw=True).get()
    assert result["status"] == "completed"
    async def check():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            clause = (await session.execute(select(Clause))).scalar_one()
            assert analysis.status == AnalysisStatus.COMPLETED
            assert analysis.processing_time_ms >= 0
            assert clause.clause_number == "1"
            assert clause.type == ClauseType.PAYMENT
            assert clause.risk_level == RiskLevel.HIGH
            assert clause.content_hash == hashlib.sha256(b"Pay.").hexdigest()
    run(check())


def test_cross_tenant_contract_is_not_read(db, monkeypatch):
    factory, (analysis_id, other_id, contract_id) = db
    async def setup():
        async with factory() as session:
            contract = await session.get(Contract, contract_id)
            contract.organization_id = other_id
            await session.commit()
    run(setup())
    monkeypatch.setattr(tasks, "get_llm_client", lambda: pytest.fail("LLM must not be called"))
    result = tasks.analyze_contract.apply(args=[str(analysis_id)], throw=True).get()
    assert result == {"error": "Contract not found or no content"}
    async def check():
        async with factory() as session:
            assert (await session.get(Analysis, analysis_id)).status == AnalysisStatus.FAILED
            assert not (await session.execute(select(Clause))).scalars().all()
    run(check())


def test_invalid_clause_rolls_back_and_marks_failed(db, monkeypatch):
    factory, (analysis_id, _, _) = db
    class Service:
        def __init__(self, _): pass
        async def analyze_contract(self, **kwargs):
            return {"clauses": [{"content": "valid"}, {"content": "bad", "type": "nonsense"}]}
    monkeypatch.setattr(tasks, "get_llm_client", lambda: object())
    monkeypatch.setattr(tasks, "AnalysisService", Service)
    with pytest.raises(ValueError):
        tasks.analyze_contract.apply(args=[str(analysis_id)], throw=True)
    async def check():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            assert analysis.status == AnalysisStatus.FAILED
            assert analysis.error_message == "Analysis processing failed"
            assert not (await session.execute(select(Clause))).scalars().all()
    run(check())


def test_transient_error_retries_then_completes(db, monkeypatch):
    factory, (analysis_id, _, _) = db
    attempts = []
    class Service:
        def __init__(self, _): pass
        async def analyze_contract(self, **kwargs):
            attempts.append(1)
            if len(attempts) == 1:
                raise TimeoutError("synthetic failure")
            return {"clauses": []}
    monkeypatch.setattr(tasks, "get_llm_client", lambda: object())
    monkeypatch.setattr(tasks, "AnalysisService", Service)
    result = tasks.analyze_contract.apply(args=[str(analysis_id)]).get(propagate=True)
    assert result["status"] == "completed"
    assert len(attempts) == 2
    async def check():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            assert analysis.status == AnalysisStatus.COMPLETED
            assert analysis.error_message is None
    run(check())


def test_exhausted_transient_error_marks_failed(db, monkeypatch):
    factory, (analysis_id, _, _) = db
    class Service:
        def __init__(self, _): pass
        async def analyze_contract(self, **kwargs):
            raise TimeoutError("private synthetic detail")
    monkeypatch.setattr(tasks, "get_llm_client", lambda: object())
    monkeypatch.setattr(tasks, "AnalysisService", Service)
    with pytest.raises(TimeoutError):
        tasks.analyze_contract.apply(args=[str(analysis_id)]).get(propagate=True)
    async def check():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            assert analysis.status == AnalysisStatus.FAILED
            assert analysis.error_message == "Analysis processing failed"
    run(check())


def test_duplicate_delivery_does_not_call_service(db, monkeypatch):
    factory, (analysis_id, _, _) = db
    async def setup():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            analysis.status = AnalysisStatus.COMPLETED
            await session.commit()
    run(setup())
    monkeypatch.setattr(tasks, "get_llm_client", lambda: pytest.fail("duplicate called LLM"))
    assert tasks.analyze_contract.apply(args=[str(analysis_id)], throw=True).get() == {
        "error": "Analysis not found or not pending"
    }


def test_invalid_identifier_is_not_retried(db):
    assert tasks.analyze_contract.apply(args=["not-a-uuid"], throw=True).get() == {
        "error": "Invalid analysis ID"
    }


def test_http_transport_timeout_is_retried(db, monkeypatch):
    import httpx
    _, (analysis_id, _, _) = db
    attempts = []
    class Service:
        def __init__(self, _): pass
        async def analyze_contract(self, **kwargs):
            attempts.append(1)
            if len(attempts) == 1:
                raise httpx.ReadTimeout("synthetic timeout")
            return {"clauses": []}
    monkeypatch.setattr(tasks, "get_llm_client", lambda: object())
    monkeypatch.setattr(tasks, "AnalysisService", Service)
    assert tasks.analyze_contract.apply(args=[str(analysis_id)]).get()["status"] == "completed"
    assert len(attempts) == 2
