"""Authenticated, record-bound execution evidence (not model-generated content)."""
import hashlib
import hmac
import json

from app.config import get_settings

_KEY = "_execution_evidence_v1"


def _mac(analysis_id, evidence):
    payload = json.dumps(["contractai-execution-v1", str(analysis_id), evidence],
                         sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hmac.new(get_settings().SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def seal_result(result, analysis_id):
    result = dict(result)
    result.pop(_KEY, None)
    evidence = result.get("llm_execution")
    if isinstance(evidence, dict):
        result[_KEY] = {"evidence": evidence, "mac": _mac(analysis_id, evidence)}
    return result


def read_evidence(result, analysis_id):
    if not isinstance(result, dict):
        return None
    envelope = result.get(_KEY)
    if not isinstance(envelope, dict) or set(envelope) != {"evidence", "mac"}:
        return None
    evidence, mac = envelope["evidence"], envelope["mac"]
    if not isinstance(evidence, dict) or not isinstance(mac, str):
        return None
    if set(evidence) != {"adapter", "effective_provider", "effective_model"}:
        return None
    if not all(v is None or isinstance(v, str) for v in evidence.values()):
        return None
    try:
        return evidence.copy() if hmac.compare_digest(_mac(analysis_id, evidence), mac) else None
    except (ValueError, TypeError):
        return None


def public_result(result):
    if not isinstance(result, dict):
        return result
    return {k: v for k, v in result.items() if k != _KEY}
