"""HTTP regression with fictional SQLite records and dependency overrides."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.analysis import router
from app.database import get_db
from app.models.analysis import Analysis
from app.models.clause import Clause, ClauseType, RiskLevel
from app.models.user import User
from app.services.auth import get_current_user_dependency
from app.tests.test_analysis_worker import db, run


@pytest.mark.parametrize("levels,result,expected_level,expected_score", [
    ([], {}, None, None),
    (["high"], {}, "high", None),
    (["low", "high", "critical"], {"overall_risk_level": "low"}, "critical", None),
    (["medium"], {"overall_risk_score": None}, "medium", None),
    (["high"], {"overall_risk_score": 0}, "high", 0),
    (["high"], {"overall_risk_score": True}, "high", None),
])
def test_result_http(db, levels, result, expected_level, expected_score):
    factory, (analysis_id, _, _) = db

    async def setup():
        async with factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            user = await session.get(User, analysis.created_by_id)
            analysis.result = result
            for level in levels:
                session.add(Clause(analysis_id=analysis.id, contract_id=analysis.contract_id,
                    organization_id=analysis.organization_id, type=ClauseType.GENERAL,
                    content="Texto fictício", content_hash="a" * 64,
                    risk_level=RiskLevel(level), risk_score=0.0, risk_factors=[]))
            await session.commit()
            return SimpleNamespace(id=user.id, organization_id=user.organization_id, is_superuser=False)
    user = run(setup())
    app = FastAPI()
    app.include_router(router, prefix="/analysis")
    async def session_override():
        async with factory() as session:
            yield session
    app.dependency_overrides[get_db] = session_override
    app.dependency_overrides[get_current_user_dependency] = lambda: user
    with TestClient(app) as client:
        response = client.get(f"/analysis/{analysis_id}/result")
    assert response.status_code == 200
    summary = response.json()["risk_summary"]
    assert summary["overall_risk_level"] == expected_level
    assert summary["overall_risk_level_source"] == ("highest_clause_risk" if expected_level else None)
    assert summary["overall_risk_score"] == expected_score
