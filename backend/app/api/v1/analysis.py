"""Analysis API endpoints - Synchronous version (no Celery/Redis required)."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditAction, AuditLog, AuditStatus
from app.models.analysis import Analysis, AnalysisStatus, AnalysisType
from app.models.contract import Contract
from app.models.user import User
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisListResponse,
    AnalysisResponse,
    AnalysisResultResponse,
)
from app.schemas.common import ErrorResponse, SuccessResponse
from app.services.auth import get_current_user_dependency
from app.services.analysis import AnalysisService
from app.services.llm_client import get_llm_client

router = APIRouter()


async def _verify_organization_access(
    current_user: User, organization_id: UUID, db: AsyncSession
) -> None:
    """Verify user has access to the organization."""
    if current_user.organization_id != organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )


async def _run_analysis_sync(
    analysis,
    contract,
    db,
    current_user,
    req,
    llm_client,
):
    """Run analysis synchronously (replaces Celery task)."""
    from app.services.clause_normalization import build_clause
    from datetime import datetime, timezone

    analysis_id = analysis.id
    user_id = current_user.id
    organization_id = current_user.organization_id
    try:
        # Update status to processing
        analysis.status = AnalysisStatus.PROCESSING
        analysis.started_at = datetime.now(timezone.utc)
        await db.commit()

        # Get LLM client and run analysis
        service = AnalysisService(llm_client)

        result = await service.analyze_contract(
            contract_text=contract.content_text,
            analysis_type=analysis.type,
            llm_provider=analysis.llm_provider,
            llm_model=analysis.llm_model,
            prompt_version=analysis.prompt_version,
        )

        # Save results
        analysis.status = AnalysisStatus.COMPLETED
        from app.services.execution_evidence import seal_result
        analysis.result = seal_result(result, analysis.id)
        analysis.completed_at = datetime.now(timezone.utc)
        analysis.processing_time_ms = int(
            (analysis.completed_at - analysis.started_at).total_seconds() * 1000
        )

        for clause_data in result.get("clauses", []):
            db.add(build_clause(clause_data, analysis.id, contract.id, analysis.organization_id))

        # Audit and result are committed together; no partial clauses on failure.
        audit = AuditLog.create(
            organization_id=organization_id,
            user_id=user_id,
            action=AuditAction.ANALYSIS_COMPLETE,
            status=AuditStatus.SUCCESS,
            resource_type="analysis",
            resource_id=str(analysis.id),
            ip_address=req.client.host if req and req.client else None,
            request_id=req.headers.get("x-request-id"),
            details={
                "clauses_found": len(result.get("clauses", [])),
                "processing_time_ms": analysis.processing_time_ms,
            },
        )
        db.add(audit)
        await db.commit()

        return True

    except Exception:
        await db.rollback()
        analysis = await db.get(Analysis, analysis_id)
        analysis.status = AnalysisStatus.FAILED
        analysis.error_message = "Analysis processing failed"
        analysis.completed_at = datetime.now(timezone.utc)
        await db.commit()

        # Audit log failure
        audit = AuditLog.create(
            organization_id=organization_id,
            user_id=user_id,
            action=AuditAction.ANALYSIS_FAILED,
            status=AuditStatus.FAILURE,
            resource_type="analysis",
            resource_id=str(analysis.id),
            ip_address=req.client.host if req and req.client else None,
            request_id=req.headers.get("x-request-id"),
            error_message="Analysis processing failed",
        )
        db.add(audit)
        await db.commit()
        raise


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new analysis (synchronous)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Contract not found"},
        500: {"model": ErrorResponse, "description": "Analysis failed"},
    },
)
async def create_analysis(
    request: AnalysisCreate,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> AnalysisResponse:
    """Create and run a new contract analysis synchronously."""
    # Verify contract exists and user has access
    contract = await db.get(Contract, request.contract_id)
    if not contract or contract.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    await _verify_organization_access(current_user, contract.organization_id, db)

    if not contract.content_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contract has no extracted text")

    # Create analysis record with PENDING status
    analysis = Analysis(
        organization_id=current_user.organization_id,
        contract_id=request.contract_id,
        created_by_id=current_user.id,
        type=request.type,
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
        prompt_version=request.prompt_version,
        status=AnalysisStatus.PENDING,
    )
    db.add(analysis)
    await db.flush()

    # Audit log start
    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.ANALYSIS_START,
        status=AuditStatus.SUCCESS,
        resource_type="analysis",
        resource_id=str(analysis.id),
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
        details={
            "contract_id": str(request.contract_id),
            "type": request.type.value,
            "llm_provider": request.llm_provider,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(analysis)

    # Get LLM client
    llm_client = get_llm_client()

    # Run analysis synchronously
    try:
        await _run_analysis_sync(
            analysis=analysis,
            contract=contract,
            db=db,
            current_user=current_user,
            req=req,
            llm_client=llm_client,
        )
        await db.refresh(analysis)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed"
        ) from None

    return AnalysisResponse.model_validate(analysis)


@router.get(
    "",
    response_model=AnalysisListResponse,
    summary="List analyses",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
    },
)
async def list_analyses(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[AnalysisStatus | None, Query()] = None,
    contract_id: Annotated[UUID | None, Query()] = None,
    type_filter: Annotated[AnalysisType | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> AnalysisListResponse:
    """List analyses for the current organization."""
    await _verify_organization_access(current_user, current_user.organization_id, db)

    query = select(Analysis).where(
        Analysis.organization_id == current_user.organization_id,
        Analysis.deleted_at.is_(None),
    )
    if status_filter:
        query = query.where(Analysis.status == status_filter)
    if contract_id:
        query = query.where(Analysis.contract_id == contract_id)
    if type_filter:
        query = query.where(Analysis.type == type_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = query.order_by(Analysis.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    analyses = result.scalars().all()

    analysis_responses = [AnalysisResponse.model_validate(a) for a in analyses]
    total_pages = (total + page_size - 1) // page_size

    return AnalysisListResponse(
        analyses=analysis_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    summary="Get analysis by ID",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Analysis not found"},
    },
)
async def get_analysis(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> AnalysisResponse:
    """Get an analysis by ID."""
    analysis = await db.get(Analysis, analysis_id)
    if not analysis or analysis.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    await _verify_organization_access(current_user, analysis.organization_id, db)

    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.ANALYSIS_VIEW,
        status=AuditStatus.SUCCESS,
        resource_type="analysis",
        resource_id=str(analysis.id),
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)
    await db.commit()

    return AnalysisResponse.model_validate(analysis)


@router.get(
    "/{analysis_id}/result",
    response_model=AnalysisResultResponse,
    summary="Get detailed analysis result with clauses and risk summary",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Analysis not found"},
    },
)
async def get_analysis_result(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> AnalysisResultResponse:
    """Get detailed analysis result including clauses and risk summary."""
    from app.models.clause import Clause, ClauseType, RiskLevel
    from app.schemas.clause import ClauseSummaryResponse, EntitySummaryResponse, RiskSummaryResponse

    analysis = await db.get(Analysis, analysis_id)
    if not analysis or analysis.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    await _verify_organization_access(current_user, analysis.organization_id, db)

    # Get clauses
    from sqlalchemy import select

    clause_result = await db.execute(
        select(Clause).where(
            Clause.analysis_id == analysis_id,
            Clause.deleted_at.is_(None),
        ).order_by(Clause.page_start, Clause.char_start)
    )
    clauses = clause_result.scalars().all()

    # Build clause summaries
    clause_summaries = [
        ClauseSummaryResponse(
            id=c.id,
            clause_number=c.clause_number,
            title=c.title,
            type=c.type.value,
            risk_level=c.risk_level.value,
            risk_score=c.risk_score,
            page_start=c.page_start,
            page_end=c.page_end,
        )
        for c in clauses
    ]

    # Build risk summary
    critical_count = sum(1 for c in clauses if c.risk_level == RiskLevel.CRITICAL)
    high_count = sum(1 for c in clauses if c.risk_level == RiskLevel.HIGH)
    medium_count = sum(1 for c in clauses if c.risk_level == RiskLevel.MEDIUM)
    low_count = sum(1 for c in clauses if c.risk_level == RiskLevel.LOW)

    all_risk_factors = []
    for c in clauses:
        all_risk_factors.extend(c.risk_factors)

    # Derive overall risk from persisted clauses, even if the model disagrees.
    # Heuristic: highest risk level present among clauses.
    # Score is only included when explicitly provided by the model.
    overall_risk_level = None
    if critical_count > 0:
        overall_risk_level = "critical"
    elif high_count > 0:
        overall_risk_level = "high"
    elif medium_count > 0:
        overall_risk_level = "medium"
    elif low_count > 0:
        overall_risk_level = "low"

    overall_risk_score = analysis.result.get("overall_risk_score")
    # Do not invent score; omit when absent or non-numeric.
    from math import isfinite
    if isinstance(overall_risk_score, bool) or not isinstance(overall_risk_score, (int, float)) or not isfinite(overall_risk_score):
        overall_risk_score = None

    risk_summary = RiskSummaryResponse(
        overall_risk_score=overall_risk_score,
        overall_risk_level=overall_risk_level,
        overall_risk_level_source="highest_clause_risk" if overall_risk_level is not None else None,
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        risk_factors=list(set(all_risk_factors)),
    )

    # Build entity summary
    entity_summary = EntitySummaryResponse(
        parties=analysis.result.get("parties", []),
        dates=analysis.result.get("dates", []),
        amounts=analysis.result.get("amounts", []),
        references=analysis.result.get("references", []),
    )

    return AnalysisResultResponse(
        analysis=AnalysisResponse.model_validate(analysis),
        clauses=clause_summaries,
        risk_summary=risk_summary,
        entity_summary=entity_summary,
    )


@router.delete(
    "/{analysis_id}",
    response_model=SuccessResponse,
    summary="Delete analysis (soft delete)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Analysis not found"},
    },
)
async def delete_analysis(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> SuccessResponse:
    """Soft delete an analysis."""
    from datetime import datetime, timezone

    analysis = await db.get(Analysis, analysis_id)
    if not analysis or analysis.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    await _verify_organization_access(current_user, analysis.organization_id, db)

    analysis.deleted_at = datetime.now(timezone.utc)

    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.ANALYSIS_DELETE,
        status=AuditStatus.SUCCESS,
        resource_type="analysis",
        resource_id=str(analysis.id),
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)
    await db.commit()

    return SuccessResponse(message="Analysis deleted successfully")