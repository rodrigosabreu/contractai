"""Celery tasks for async processing."""
import asyncio
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx

from celery import shared_task
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_context
from app.models.audit_log import AuditLog
from app.models.token_blacklist import TokenBlacklist
from app.models.contract import Contract, ContractStatus
from app.models.analysis import Analysis, AnalysisStatus
from app.services.analysis import AnalysisService
from app.services.llm_client import get_llm_client
from app.services.pdf_parser import extract_text_from_pdf

RETRYABLE_ANALYSIS_ERRORS = (ConnectionError, TimeoutError, httpx.TimeoutException, httpx.NetworkError)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def analyze_contract(self, analysis_id: str) -> dict:
    """Analyze one pending record. The analysis ID is an internal trusted queue input."""
    from app.services.clause_normalization import build_clause

    async def _analyze():
        async with get_db_context() as db:
            try:
                identifier = UUID(analysis_id)
            except (ValueError, TypeError, AttributeError):
                return {"error": "Invalid analysis ID"}

            # A conditional update prevents duplicate deliveries from both claiming work.
            started = datetime.now(timezone.utc)
            claimed = await db.execute(
                update(Analysis).where(
                    Analysis.id == identifier,
                    Analysis.status == AnalysisStatus.PENDING,
                    Analysis.deleted_at.is_(None),
                ).values(status=AnalysisStatus.PROCESSING, started_at=started,
                         completed_at=None, error_message=None)
            )
            await db.commit()
            if not claimed.rowcount:
                return {"error": "Analysis not found or not pending"}

            analysis = await db.get(Analysis, identifier)
            contract = (await db.execute(select(Contract).where(
                Contract.id == analysis.contract_id,
                Contract.organization_id == analysis.organization_id,
                Contract.deleted_at.is_(None),
            ))).scalar_one_or_none()
            if not contract or not contract.content_text:
                analysis.status = AnalysisStatus.FAILED
                analysis.error_message = "Contract not found or no content"
                analysis.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return {"error": "Contract not found or no content"}

            clock_start = time.monotonic()
            try:
                service = AnalysisService(get_llm_client())
                result = await service.analyze_contract(
                    contract_text=contract.content_text,
                    analysis_type=analysis.type.value,
                    llm_provider=analysis.llm_provider,
                    llm_model=analysis.llm_model,
                    prompt_version=analysis.prompt_version,
                )
                if not isinstance(result, dict) or not isinstance(result.get("clauses", []), list):
                    raise ValueError("Invalid analysis result")
                for data in result.get("clauses", []):
                    db.add(build_clause(data, analysis.id, contract.id, analysis.organization_id))
                analysis.status = AnalysisStatus.COMPLETED
                from app.services.execution_evidence import seal_result
                analysis.result = seal_result(result, analysis.id)
                analysis.completed_at = datetime.now(timezone.utc)
                analysis.processing_time_ms = int((time.monotonic() - clock_start) * 1000)
                await db.commit()
                return {"status": "completed", "analysis_id": str(identifier),
                        "clauses_found": len(result.get("clauses", []))}
            except Exception as exc:
                # A failed flush invalidates the transaction; never commit partial clauses.
                await db.rollback()
                analysis = await db.get(Analysis, identifier)
                retryable = isinstance(exc, RETRYABLE_ANALYSIS_ERRORS)
                will_retry = retryable and self.request.retries < self.max_retries
                analysis.status = AnalysisStatus.PENDING if will_retry else AnalysisStatus.FAILED
                # Avoid persisting provider exceptions that can contain sensitive content.
                analysis.error_message = "Analysis processing failed"
                analysis.completed_at = None if will_retry else datetime.now(timezone.utc)
                await db.commit()
                raise

    try:
        return asyncio.run(_analyze())
    except RETRYABLE_ANALYSIS_ERRORS as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def sync_connector(self, connector_id: str, full_sync: bool = False) -> dict:
    """
    Sync files from external storage connector.
    
    Args:
        connector_id: UUID of the connector
        full_sync: Whether to do full sync or incremental
        
    Returns:
        Dict with sync results
    """
    async def _sync():
        async with get_db_context() as db:
            from app.models.connector import Connector
            from app.services.connectors import get_connector_service
            
            connector = await db.get(Connector, UUID(connector_id))
            if not connector or not connector.is_active:
                return {"error": "Connector not found or inactive"}
            
            service = get_connector_service(connector.type)
            
            try:
                result = await service.sync(
                    connector=connector,
                    full_sync=full_sync,
                )
                
                connector.last_sync_at = datetime.now(timezone.utc)
                await db.commit()
                
                return {
                    "status": "completed",
                    "connector_id": str(connector.id),
                    "files_synced": result.get("files_synced", 0),
                    "errors": result.get("errors", []),
                }
            except Exception as e:
                return {"error": str(e)}
    
    return asyncio.run(_sync())


@shared_task
def cleanup_expired_tokens() -> dict:
    """Remove expired tokens from blacklist."""
    async def _cleanup():
        async with get_db_context() as db:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                delete(TokenBlacklist).where(TokenBlacklist.expires_at < now)
            )
            await db.commit()
            return {"deleted_count": result.rowcount}
    
    return asyncio.run(_cleanup())


@shared_task
def cleanup_old_audit_logs() -> dict:
    """Remove audit logs older than retention period."""
    async def _cleanup():
        async with get_db_context() as db:
            from app.config import get_settings
            settings = get_settings()
            
            cutoff = datetime.now(timezone.utc) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
            result = await db.execute(
                delete(AuditLog).where(AuditLog.created_at < cutoff)
            )
            await db.commit()
            return {"deleted_count": result.rowcount}
    
    return asyncio.run(_cleanup())


@shared_task
def extract_contract_text(contract_id: str) -> dict:
    """Extract text from contract PDF."""
    async def _extract():
        async with get_db_context() as db:
            contract = await db.get(Contract, UUID(contract_id))
            if not contract or not contract.file_path:
                return {"error": "Contract not found or no file"}
            
            try:
                text = await extract_text_from_pdf(contract.file_path)
                
                contract.content_text = text
                contract.status = ContractStatus.PARSED
                contract.page_count = len(text.split("\f")) if text else 0
                await db.commit()
                
                return {
                    "status": "completed",
                    "contract_id": str(contract.id),
                    "pages": contract.page_count,
                    "chars": len(text) if text else 0,
                }
            except Exception as e:
                contract.status = ContractStatus.ERROR
                contract.error_message = str(e)
                await db.commit()
                raise
    
    return asyncio.run(_extract())