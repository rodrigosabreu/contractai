"""Regression tests using fictional model responses."""
import pytest

from app.services.analysis import AnalysisService


@pytest.mark.parametrize("text_field,explanation_field", [("excerpt", "analysis"), ("trecho", "analise")])
def test_aliases_and_summary(text_field, explanation_field):
    service = AnalysisService(llm_client=object())
    result = service._validate_and_enhance_result({"clauses": [{
        text_field: "Pagamento fictício.", "risk": "high", explanation_field: "Prazo ausente.",
    }]}, "full")
    clause = result["clauses"][0]
    assert clause["content"] == "Pagamento fictício."
    assert clause["risk_level"] == "high"
    assert clause["risk_explanation"] == "Prazo ausente."
    assert result["risk_summary"]["high_risk"] == 1
    assert result["risk_summary"]["low_risk"] == 0


@pytest.mark.parametrize("clause", [
    {"content": "Texto fictício."},
    {"content": "Texto fictício.", "risk": "desconhecido"},
    {"content": " ", "risk": "high"},
    {"risk": "high"},
])
def test_invalid_clause_fails_without_inventing_low_risk(clause):
    with pytest.raises(ValueError):
        AnalysisService(llm_client=object())._validate_and_enhance_result({"clauses": [clause]}, "full")
