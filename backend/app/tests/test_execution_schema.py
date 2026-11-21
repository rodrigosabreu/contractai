from uuid import uuid4
from app.services.execution_evidence import seal_result


def test_schema_verifies_and_does_not_serialize_signature():
    from datetime import datetime, timezone
    from app.schemas.analysis import AnalysisResponse, AnalysisListResponse
    ident = uuid4()
    evidence = {'adapter': 'hermes', 'effective_provider': None, 'effective_model': None}
    data = dict(id=ident, contract_id=uuid4(), organization_id=uuid4(), created_by_id=uuid4(),
                status='completed', input_tokens=None, output_tokens=None, total_cost_usd=None,
                processing_time_ms=None, result=seal_result({'llm_execution': evidence}, ident),
                error_message=None, started_at=None, completed_at=None,
                created_at=datetime.now(timezone.utc), updated_at=None, deleted_at=None)
    item = AnalysisResponse.model_validate(data)
    nested = AnalysisListResponse(analyses=[item], total=1, page=1, page_size=1,
                                  total_pages=1, has_next=False, has_prev=False).model_dump()
    assert nested['analyses'][0]['execution_evidence'] == evidence
    assert '_execution_evidence_v1' not in nested['analyses'][0]['result']
    data['id'] = uuid4()
    assert AnalysisResponse.model_validate(data).execution_evidence is None
