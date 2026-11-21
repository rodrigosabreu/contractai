"""Regression for Hermes' observed clause field names."""
import hashlib

import pytest
from sqlalchemy import select

from app.models.analysis import Analysis, AnalysisStatus
from app.models.clause import Clause, RiskLevel
from app.workers import tasks
from app.tests.test_analysis_worker import db, run  # reuse isolated SQLite fixture


@pytest.mark.parametrize('text_field,explanation_field', [('excerpt', 'analysis'), ('trecho', 'analise')])
def test_worker_persists_hermes_excerpt_and_risk(db, monkeypatch, text_field, explanation_field):
    factory, (analysis_id, _, _) = db

    class Service:
        def __init__(self, _):
            pass

        async def analyze_contract(self, **kwargs):
            return {"clauses": [{"type": "payment", "title": "Pagamento",
                                  text_field: "Pagamento mensal.", "risk": "high",
                                  explanation_field: "Vencimento ausente."}]}

    monkeypatch.setattr(tasks, "get_llm_client", lambda: object())
    monkeypatch.setattr(tasks, "AnalysisService", Service)
    result = tasks.analyze_contract.apply(args=[str(analysis_id)], throw=True).get()
    assert result["status"] == "completed"

    async def check():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            clause = (await session.execute(select(Clause))).scalar_one()
            assert analysis.status == AnalysisStatus.COMPLETED
            assert clause.content == "Pagamento mensal."
            assert clause.content_hash == hashlib.sha256(clause.content.encode()).hexdigest()
            assert clause.risk_level == RiskLevel.HIGH
            assert clause.risk_explanation == "Vencimento ausente."
    run(check())
