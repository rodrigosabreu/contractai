"""HTTP regression tests for GET /analysis/{id}/result risk summary."""
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.api.v1.analysis import _run_analysis_sync, get_analysis_result
from app.models.analysis import Analysis, AnalysisStatus
from app.models.clause import Clause, RiskLevel
from app.models.contract import Contract
from app.models.user import User
from app.tests.test_analysis_worker import db, run


@pytest.mark.parametrize("clause_risks,expected_level", [
    (["high"], "high"),
    (["critical"], "critical"),
    (["medium"], "medium"),
    (["low"], "low"),
    (["high", "medium"], "high"),
    (["critical", "high", "low"], "critical"),
    (["medium", "low"], "medium"),
    ([], None),
])
def test_derives_overall_risk_from_clauses(db, monkeypatch, clause_risks, expected_level):
    factory, (analysis_id, _, _) = db
    clauses_data = [{"content": f"Cláusula fictícia {i}", "risk": r} for i, r in enumerate(clause_risks, 1)]
    class Model:
        async def complete(self, **kwargs):
            return SimpleNamespace(content=json.dumps({"clauses": clauses_data}))
    async def sync():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            contract = await session.get(Contract, analysis.contract_id)
            user = await session.get(User, analysis.created_by_id)
            await _run_analysis_sync(analysis, contract, session, user, SimpleNamespace(client=None, headers={}), Model())
    run(sync())
    async def check():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            result = await get_analysis_result(analysis_id, session, SimpleNamespace(client=None, headers={}), await session.get(User, analysis.created_by_id))
            assert result.risk_summary.overall_risk_level == expected_level
            assert result.risk_summary.overall_risk_score is None
    run(check())


@pytest.mark.parametrize("model_score,expected", [
    (0.75, 0.75),
    (0, 0),
    ("0.5", None),
    (None, None),
    ({}, None),
])
def test_score_only_when_numeric(db, monkeypatch, model_score, expected):
    factory, (analysis_id, _, _) = db
    result_data = {"clauses": [{"content": "Fictício", "risk": "high"}]}
    if model_score is not None:
        result_data["overall_risk_score"] = model_score
    class Model:
        async def complete(self, **kwargs):
            return SimpleNamespace(content=json.dumps(result_data))
    async def sync():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            contract = await session.get(Contract, analysis.contract_id)
            user = await session.get(User, analysis.created_by_id)
            await _run_analysis_sync(analysis, contract, session, user, SimpleNamespace(client=None, headers={}), Model())
    run(sync())
    async def check():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            result = await get_analysis_result(analysis_id, session, SimpleNamespace(client=None, headers={}), await session.get(User, analysis.created_by_id))
            assert result.risk_summary.overall_risk_score == expected
    run(check())


def test_result_includes_counts_and_factors(db, monkeypatch):
    factory, (analysis_id, _, _) = db
    clauses_data = [
        {"content": "A", "risk": "high", "risk_factors": ["f1"]},
        {"content": "B", "risk": "low", "risk_factors": ["f2", "f1"]},
    ]
    class Model:
        async def complete(self, **kwargs):
            return SimpleNamespace(content=json.dumps({"clauses": clauses_data}))
    async def sync():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            contract = await session.get(Contract, analysis.contract_id)
            user = await session.get(User, analysis.created_by_id)
            await _run_analysis_sync(analysis, contract, session, user, SimpleNamespace(client=None, headers={}), Model())
    run(sync())
    async def check():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            result = await get_analysis_result(analysis_id, session, SimpleNamespace(client=None, headers={}), await session.get(User, analysis.created_by_id))
            assert result.risk_summary.high_count == 1
            assert result.risk_summary.low_count == 1
            assert result.risk_summary.critical_count == 0
            assert result.risk_summary.medium_count == 0
            assert set(result.risk_summary.risk_factors) == {"f1", "f2"}
    run(check())