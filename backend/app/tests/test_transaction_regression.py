"""A database flush error must not commit any clause."""
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.v1.analysis import _run_analysis_sync
from app.models.analysis import Analysis, AnalysisStatus
from app.models.clause import Clause
from app.models.contract import Contract
from app.models.user import User
from app.services import clause_normalization
from app.tests.test_analysis_worker import db, run
from app.workers import tasks


@pytest.mark.parametrize("path", ["sync", "worker"])
def test_failed_flush_rolls_back_all_clauses(db, monkeypatch, path):
    factory, (analysis_id, _, _) = db
    real_build = clause_normalization.build_clause
    calls = []
    def invalid_second(*args):
        clause = real_build(*args)
        calls.append(1)
        if len(calls) == 2:
            clause.content_hash = None
        return clause
    monkeypatch.setattr(clause_normalization, "build_clause", invalid_second)
    class Model:
        async def complete(self, **kwargs):
            return SimpleNamespace(content=json.dumps({"clauses": [
                {"content": "Fictício A", "risk": "high"},
                {"content": "Fictício B", "risk": "low"},
            ]}))
    if path == "worker":
        monkeypatch.setattr(tasks, "get_llm_client", lambda: Model())
        with pytest.raises(IntegrityError):
            tasks.analyze_contract.apply(args=[str(analysis_id)], throw=True).get()
    else:
        async def sync():
            async with factory() as session:
                analysis = await session.get(Analysis, analysis_id)
                contract = await session.get(Contract, analysis.contract_id)
                user = await session.get(User, analysis.created_by_id)
                with pytest.raises(IntegrityError):
                    await _run_analysis_sync(analysis, contract, session, user, SimpleNamespace(client=None, headers={}), Model())
        run(sync())
    async def check():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            assert analysis.status == AnalysisStatus.FAILED
            assert not (await session.execute(select(Clause))).scalars().all()
    run(check())
