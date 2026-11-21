"""Contract summaries use the analysis lifecycle, not contract lifecycle."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.analysis import AnalysisStatus
from app.models.contract import ContractStatus
from app.schemas.contract import ContractResponse


@pytest.mark.parametrize("status", list(AnalysisStatus))
def test_latest_analysis_status_uses_analysis_lifecycle(status):
    now = datetime.now(timezone.utc)
    contract = ContractResponse(
        id=uuid4(), organization_id=uuid4(), owner_id=uuid4(),
        title="Test", status=ContractStatus.UPLOADED, meta={},
        file_path=None, file_size=None, mime_type=None, content_hash=None,
        page_count=None, error_message=None, created_at=now, updated_at=now,
        deleted_at=None, latest_analysis_status=status,
    )
    assert contract.latest_analysis_status == status
