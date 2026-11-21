"""Normalize and validate untrusted model clauses for both processing paths."""
import hashlib

from app.models.clause import Clause, ClauseType, RiskLevel


def normalize_clause(data):
    if not isinstance(data, dict):
        raise ValueError("Invalid clause content")
    normalized = data.copy()
    for canonical, aliases in (
        ("content", ("excerpt", "trecho")),
        ("risk_level", ("risk",)),
        ("risk_explanation", ("analysis", "analise")),
        ("clause_number", ("number",)),
    ):
        if normalized.get(canonical) is None or normalized.get(canonical) == "":
            for alias in aliases:
                if normalized.get(alias) is not None and normalized.get(alias) != "":
                    normalized[canonical] = normalized[alias]
                    break
    content = normalized.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Invalid clause content")
    risk = normalized.get("risk_level")
    if not isinstance(risk, str):
        raise ValueError("Missing or invalid clause risk level")
    try:
        normalized["risk_level"] = RiskLevel(risk.strip().lower()).value
    except ValueError:
        raise ValueError("Missing or invalid clause risk level") from None
    try:
        normalized["type"] = ClauseType(normalized.get("type", "general")).value
    except (ValueError, TypeError):
        raise ValueError("Invalid clause type") from None
    return normalized


def build_clause(data, analysis_id, contract_id, organization_id):
    data = normalize_clause(data)
    content = data["content"]
    return Clause(
        analysis_id=analysis_id, contract_id=contract_id, organization_id=organization_id,
        clause_number=data.get("clause_number"), title=data.get("title"),
        type=ClauseType(data["type"]), content=content,
        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        page_start=data.get("page_start"), page_end=data.get("page_end"),
        char_start=data.get("char_start"), char_end=data.get("char_end"),
        risk_score=data.get("risk_score", 0.0), risk_level=RiskLevel(data["risk_level"]),
        risk_factors=data.get("risk_factors", []),
        risk_explanation=data.get("risk_explanation"), entities=data.get("entities", {}),
    )
