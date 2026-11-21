"""Fictional model output through both analysis paths and real SQLite."""
import hashlib
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.api.v1.analysis import _run_analysis_sync
from app.models.analysis import Analysis, AnalysisStatus
from app.models.clause import Clause, RiskLevel
from app.models.contract import Contract
from app.models.user import User
from app.tests.test_analysis_worker import db, run
from app.workers import tasks


class Model:
    def __init__(self, clauses):
        self.clauses = clauses

    async def complete(self, **kwargs):
        return SimpleNamespace(content=json.dumps({"clauses": self.clauses}))


@pytest.mark.parametrize("path", ["sync", "worker"])
@pytest.mark.parametrize("text_field", ["excerpt", "trecho"])
def test_alias_and_summary_persisted(db, monkeypatch, path, text_field):
    factory, (analysis_id, _, _) = db
    model = Model([{text_field: "Texto fictício.", "risk": "high", "analysis": "Prazo fictício."}])
    if path == "worker":
        monkeypatch.setattr(tasks, "get_llm_client", lambda: model)
        tasks.analyze_contract.apply(args=[str(analysis_id)], throw=True).get()
    else:
        async def sync():
            async with factory() as session:
                analysis = await session.get(Analysis, analysis_id)
                contract = await session.get(Contract, analysis.contract_id)
                user = await session.get(User, analysis.created_by_id)
                await _run_analysis_sync(analysis, contract, session, user, SimpleNamespace(client=None, headers={}), model)
        run(sync())
    async def check():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            clause = (await session.execute(select(Clause))).scalar_one()
            assert analysis.status == AnalysisStatus.COMPLETED
            assert clause.content == "Texto fictício."
            assert clause.content_hash == hashlib.sha256(clause.content.encode()).hexdigest()
            assert clause.risk_level == RiskLevel.HIGH
            assert clause.risk_explanation == "Prazo fictício."
            assert analysis.result["risk_summary"]["high_risk"] == 1
            assert analysis.result["risk_summary"]["low_risk"] == 0
    run(check())


@pytest.mark.parametrize("path", ["sync", "worker"])
@pytest.mark.parametrize("bad", [{"content": "Texto fictício."}, {"content": "Texto fictício.", "risk": "unknown"}, {"risk": "high"}])
def test_invalid_output_has_no_partial_clauses(db, monkeypatch, path, bad):
    factory, (analysis_id, _, _) = db
    model = Model([{"content": "Válida fictícia.", "risk": "high"}, bad])
    if path == "worker":
        monkeypatch.setattr(tasks, "get_llm_client", lambda: model)
        with pytest.raises(ValueError):
            tasks.analyze_contract.apply(args=[str(analysis_id)], throw=True).get()
    else:
        async def sync():
            async with factory() as session:
                analysis = await session.get(Analysis, analysis_id)
                contract = await session.get(Contract, analysis.contract_id)
                user = await session.get(User, analysis.created_by_id)
                with pytest.raises(ValueError):
                    await _run_analysis_sync(analysis, contract, session, user, SimpleNamespace(client=None, headers={}), model)
        run(sync())
    async def check():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            assert analysis.status == AnalysisStatus.FAILED
            assert not (await session.execute(select(Clause))).scalars().all()
    run(check())
