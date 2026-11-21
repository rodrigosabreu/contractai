"""Clause API endpoints."""
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditAction, AuditLog, AuditStatus
from app.models.clause import Clause, ClauseType, RiskLevel
from app.models.contract import Contract
from app.models.user import User
from app.schemas.clause import (
    ClauseListResponse,
    ClauseResponse,
    ClauseSearchRequest,
    ClauseSearchResponse,
    ClauseUpdate,
)
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.services.auth import get_current_user_dependency

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


@router.get(
    "",
    response_model=PaginatedResponse[ClauseResponse],
    summary="List clauses with filters",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
    },
)
async def list_clauses(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    analysis_id: UUID | None = Query(None, description="Filter by analysis"),
    contract_id: UUID | None = Query(None, description="Filter by contract"),
    type: str | None = Query(None, description="Filter by clause type"),
    risk_level: str | None = Query(None, description="Filter by risk level"),
    risk_score_min: float | None = Query(None, ge=0.0, le=1.0, description="Minimum risk score"),
    risk_score_max: float | None = Query(None, ge=0.0, le=1.0, description="Maximum risk score"),
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
):
    """List clauses with various filters."""
    await _verify_organization_access(current_user, current_user.organization_id, db)

    query = select(Clause).where(
        Clause.organization_id == current_user.organization_id,
    )

    if analysis_id:
        query = query.where(Clause.analysis_id == analysis_id)
    if contract_id:
        query = query.where(Clause.contract_id == contract_id)
    if type:
        query = query.where(Clause.type == type)
    if risk_level:
        query = query.where(Clause.risk_level == risk_level)
    if risk_score_min is not None:
        query = query.where(Clause.risk_score >= risk_score_min)
    if risk_score_max is not None:
        query = query.where(Clause.risk_score <= risk_score_max)

    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    query = query.order_by(Clause.risk_score.desc(), Clause.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    clauses = result.scalars().all()

    from app.schemas.common import PaginatedResponse as PR
    from app.schemas.clause import ClauseResponse as CR
    return PR.create(
        items=[CR.model_validate(c) for c in clauses],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{clause_id}",
    response_model=ClauseResponse,
    summary="Get clause by ID",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Clause not found"},
    },
)
async def get_clause(
    clause_id: UUID,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
):
    """Get a specific clause."""
    clause = await db.get(Clause, clause_id)
    if not clause or clause.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Clause not found")

    return ClauseResponse.model_validate(clause)


@router.patch(
    "/{clause_id}",
    response_model=ClauseResponse,
    summary="Update clause risk assessment (analyst/admin)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Clause not found"},
    },
)
async def update_clause(
    clause_id: UUID,
    request: ClauseUpdate,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
):
    """Update clause risk assessment."""
    from app.models.user import UserRole
    if current_user.role not in ("analyst", "admin", "manager") and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Analyst, admin, or manager role required")

    clause = await db.get(Clause, clause_id)
    if not clause or clause.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Clause not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(clause, field, value)

    clause.updated_at = datetime.now(clause.created_at.tzinfo)

    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.CLAUSE_VIEW,  # Using existing action type
        resource_type="clause",
        resource_id=str(clause.id),
        status="success",
        details={"updated_fields": list(update_data.keys())},
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(clause)

    return ClauseResponse.model_validate(clause)


@router.post(
    "/search",
    response_model=ClauseSearchResponse,
    summary="Semantic search clauses",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
    },
)
async def search_clauses(
    request: ClauseSearchRequest,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
):
    """Semantic search clauses using vector similarity."""
    await _verify_organization_access(current_user, current_user.organization_id, db)

    # TODO: Implement actual vector search using pgvector
    # For now, return empty results with proper structure
    from app.schemas.clause import ClauseSearchResponse as CSR

    return CSR(
        clauses=[],
        total=0,
        query=request.query,
        took_ms=0,
    )


@router.post(
    "/bulk-risk-update",
    response_model=dict,
    summary="Bulk update risk levels (admin)",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
    },
)
async def bulk_update_risk(
    clause_ids: list[UUID],
    risk_level: str,
    risk_score: float,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
):
    """Bulk update risk level for multiple clauses (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required")

    try:
        rl = RiskLevel(risk_level)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid risk level")

    if not 0 <= risk_score <= 1:
        raise HTTPException(status_code=400, detail="Risk score must be between 0 and 1")

    # Update clauses
    result = await db.execute(
        select(Clause).where(
            Clause.id.in_(clause_ids),
            Clause.organization_id == current_user.organization_id,
        )
    )
    clauses = result.scalars().all()

    updated = 0
    for clause in clauses:
        clause.risk_level = rl
        clause.risk_score = risk_score
        clause.updated_at = datetime.now(clause.created_at.tzinfo)
        updated += 1

    await db.commit()

    return {
        "updated": updated,
        "message": f"Updated {updated} clauses to risk_level={risk_level}, risk_score={risk_score}",
    }


@router.get(
    "/statistics/risk-distribution",
    response_model=dict,
    summary="Get risk level distribution for organization",
)
async def risk_distribution(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Get risk level distribution statistics."""
    from sqlalchemy import case

    stmt = select(
        Clause.risk_level,
        func.count(Clause.id).label("count")
    ).where(
        Clause.organization_id == current_user.organization_id
    ).group_by(Clause.risk_level)

    result = await db.execute(stmt)
    distribution = {row.risk_level.value: row.count for row in result}

    # Also get type distribution
    type_stmt = select(
        Clause.type,
        func.count(Clause.id).label("count")
    ).where(
        Clause.organization_id == current_user.organization_id
    ).group_by(Clause.type)

    type_result = await db.execute(type_stmt)
    type_distribution = {row.type.value: row.count for row in type_result}

    return {
        "risk_distribution": distribution,
        "type_distribution": type_distribution,
        "total_clauses": sum(distribution.values()),
    }


@router.get(
    "/statistics/high-risk",
    response_model=ClauseListResponse,
    summary="Get high risk clauses",
)
async def high_risk_clauses(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Get high and critical risk clauses."""
    query = select(Clause).where(
        Clause.organization_id == current_user.organization_id,
        Clause.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL]),
    ).order_by(Clause.risk_score.desc())

    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    clauses = result.scalars().all()

    from app.schemas.common import PaginatedResponse as PR
    from app.schemas.clause import ClauseResponse as CR
    return PR.create(
        items=[CR.model_validate(c) for c in clauses],
        total=total,
        page=page,
        page_size=page_size,
    )