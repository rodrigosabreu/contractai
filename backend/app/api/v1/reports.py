"""Reports API endpoints."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditAction, AuditLog, AuditStatus
from app.models.analysis import Analysis
from app.models.clause import Clause, RiskLevel
from app.models.contract import Contract
from app.models.user import User
from app.schemas.common import ErrorResponse, SuccessResponse
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
    "/organization/summary",
    summary="Get organization summary report",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
    },
)
async def organization_summary(
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> dict:
    """Get summary statistics for the organization."""
    await _verify_organization_access(current_user, current_user.organization_id, db)

    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Count contracts
    total_contracts = await db.scalar(
        select(func.count(Contract.id)).where(
            Contract.organization_id == current_user.organization_id,
            Contract.deleted_at.is_(None),
        )
    ) or 0

    contracts_this_month = await db.scalar(
        select(func.count(Contract.id)).where(
            Contract.organization_id == current_user.organization_id,
            Contract.deleted_at.is_(None),
            Contract.created_at >= month_start,
        )
    ) or 0

    # Count analyses
    total_analyses = await db.scalar(
        select(func.count(Analysis.id)).where(
            Analysis.organization_id == current_user.organization_id,
            Analysis.deleted_at.is_(None),
        )
    ) or 0

    analyses_this_month = await db.scalar(
        select(func.count(Analysis.id)).where(
            Analysis.organization_id == current_user.organization_id,
            Analysis.deleted_at.is_(None),
            Analysis.created_at >= month_start,
        )
    ) or 0

    # Count users
    total_users = await db.scalar(
        select(func.count(User.id)).where(
            User.organization_id == current_user.organization_id,
            User.deleted_at.is_(None),
        )
    ) or 0

    active_users = await db.scalar(
        select(func.count(User.id)).where(
            User.organization_id == current_user.organization_id,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
    ) or 0

    # Storage used
    storage_used = await db.scalar(
        select(func.sum(Contract.file_size)).where(
            Contract.organization_id == current_user.organization_id,
            Contract.deleted_at.is_(None),
        )
    ) or 0

    storage_used_mb = storage_used / (1024 * 1024)

    # Connectors
    from app.models.organization import Connector

    connectors = await db.execute(
        select(Connector.type, func.count(Connector.id)).where(
            Connector.organization_id == current_user.organization_id,
            Connector.deleted_at.is_(None),
            Connector.is_active.is_(True),
        ).group_by(Connector.type)
    )
    connector_counts = {row[0]: row[1] for row in connectors.all()}

    # Risk distribution
    risk_distribution = await db.execute(
        select(Clause.risk_level, func.count(Clause.id)).join(Analysis).where(
            Analysis.organization_id == current_user.organization_id,
            Clause.deleted_at.is_(None),
            Analysis.deleted_at.is_(None),
        ).group_by(Clause.risk_level)
    )
    risk_counts = {row[0].value: row[1] for row in risk_distribution.all()}

    # Audit log
    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.ANALYSIS_EXPORT,
        status=AuditStatus.SUCCESS,
        resource_type="report",
        resource_id="organization_summary",
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)
    await db.commit()

    return {
        "organization_id": str(current_user.organization_id),
        "total_users": total_users,
        "active_users": active_users,
        "total_contracts": total_contracts,
        "contracts_this_month": contracts_this_month,
        "total_analyses": total_analyses,
        "analyses_this_month": analyses_this_month,
        "storage_used_mb": round(storage_used_mb, 2),
        "connectors": connector_counts,
        "risk_distribution": risk_counts,
    }


@router.get(
    "/contracts/risk-summary",
    summary="Get contract risk summary report",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
    },
)
async def contract_risk_summary(
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> dict:
    """Get risk summary across all contracts."""
    await _verify_organization_access(current_user, current_user.organization_id, db)

    # Get high-risk contracts
    from sqlalchemy import select, func
    from app.models.analysis import Analysis, AnalysisStatus
    from app.models.clause import Clause, RiskLevel

    # Contracts with critical/high risk clauses
    high_risk_contracts = await db.execute(
        select(
            Contract.id,
            Contract.title,
            func.count(Clause.id).label("clause_count"),
            func.max(Clause.risk_score).label("max_risk_score"),
            func.sum(func.case((Clause.risk_level == RiskLevel.CRITICAL, 1), else_=0)).label("critical_count"),
            func.sum(func.case((Clause.risk_level == RiskLevel.HIGH, 1), else_=0)).label("high_count"),
        )
        .join(Analysis, Analysis.contract_id == Contract.id)
        .join(Clause, Clause.analysis_id == Analysis.id)
        .where(
            Contract.organization_id == current_user.organization_id,
            Contract.deleted_at.is_(None),
            Analysis.deleted_at.is_(None),
            Clause.deleted_at.is_(None),
            Clause.risk_level.in_([RiskLevel.CRITICAL, RiskLevel.HIGH]),
        )
        .group_by(Contract.id, Contract.title)
        .order_by(func.max(Clause.risk_score).desc())
        .limit(20)
    )

    high_risk_list = [
        {
            "contract_id": str(row.id),
            "title": row.title,
            "clause_count": row.clause_count,
            "max_risk_score": float(row.max_risk_score) if row.max_risk_score else 0.0,
            "critical_count": int(row.critical_count) if row.critical_count else 0,
            "high_count": int(row.high_count) if row.high_count else 0,
        }
        for row in high_risk_contracts.all()
    ]

    # Overall risk stats
    total_clauses = await db.scalar(
        select(func.count(Clause.id)).join(Analysis).where(
            Analysis.organization_id == current_user.organization_id,
            Analysis.deleted_at.is_(None),
            Clause.deleted_at.is_(None),
        )
    ) or 0

    avg_risk_score = await db.scalar(
        select(func.avg(Clause.risk_score)).join(Analysis).where(
            Analysis.organization_id == current_user.organization_id,
            Analysis.deleted_at.is_(None),
            Clause.deleted_at.is_(None),
        )
    ) or 0.0

    # Audit log
    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.ANALYSIS_EXPORT,
        status=AuditStatus.SUCCESS,
        resource_type="report",
        resource_id="contract_risk_summary",
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)
    await db.commit()

    return {
        "organization_id": str(current_user.organization_id),
        "total_clauses_analyzed": total_clauses,
        "average_risk_score": round(float(avg_risk_score), 4),
        "high_risk_contracts": high_risk_list,
    }


@router.get(
    "/clauses/by-type",
    summary="Get clause distribution by type",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
    },
)
async def clause_by_type(
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> dict:
    """Get clause count and risk distribution by type."""
    await _verify_organization_access(current_user, current_user.organization_id, db)

    from app.models.clause import Clause, ClauseType

    # Clause count by type
    type_counts = await db.execute(
        select(Clause.type, func.count(Clause.id)).join(Analysis).where(
            Analysis.organization_id == current_user.organization_id,
            Analysis.deleted_at.is_(None),
            Clause.deleted_at.is_(None),
        ).group_by(Clause.type)
    )
    type_distribution = {row[0].value: row[1] for row in type_counts.all()}

    # Risk by type
    risk_by_type = await db.execute(
        select(Clause.type, Clause.risk_level, func.count(Clause.id)).join(Analysis).where(
            Analysis.organization_id == current_user.organization_id,
            Analysis.deleted_at.is_(None),
            Clause.deleted_at.is_(None),
        ).group_by(Clause.type, Clause.risk_level)
    )

    risk_matrix = {}
    for row in risk_by_type.all():
        t = row[0].value
        r = row[1].value
        c = row[2]
        if t not in risk_matrix:
            risk_matrix[t] = {}
        risk_matrix[t][r] = c

    # Audit log
    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.CLAUSE_EXPORT,
        status=AuditStatus.SUCCESS,
        resource_type="report",
        resource_id="clause_by_type",
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)
    await db.commit()

    return {
        "organization_id": str(current_user.organization_id),
        "type_distribution": type_distribution,
        "risk_by_type": risk_matrix,
    }


@router.get(
    "/users/activity",
    summary="Get user activity report",
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
    },
)
async def user_activity(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    db: AsyncSession = Depends(get_db),
    req: Request = None,
    current_user: User = Depends(get_current_user_dependency),
) -> dict:
    """Get user activity summary for the organization."""
    from datetime import datetime, timedelta, timezone

    await _verify_organization_access(current_user, current_user.organization_id, db)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Get all users in org
    users_result = await db.execute(
        select(User).where(
            User.organization_id == current_user.organization_id,
            User.deleted_at.is_(None),
        )
    )
    users = users_result.scalars().all()

    # Build activity for each user
    activity = []
    for user in users:
        # Login count (audit logs)
        login_count = await db.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.organization_id == current_user.organization_id,
                AuditLog.user_id == user.id,
                AuditLog.action == AuditAction.LOGIN,
                AuditLog.created_at >= cutoff,
            )
        ) or 0

        # Contracts uploaded
        contracts_uploaded = await db.scalar(
            select(func.count(Contract.id)).where(
                Contract.organization_id == current_user.organization_id,
                Contract.owner_id == user.id,
                Contract.deleted_at.is_(None),
                Contract.created_at >= cutoff,
            )
        ) or 0

        # Analyses created
        analyses_created = await db.scalar(
            select(func.count(Analysis.id)).where(
                Analysis.organization_id == current_user.organization_id,
                Analysis.created_by_id == user.id,
                Analysis.deleted_at.is_(None),
                Analysis.created_at >= cutoff,
            )
        ) or 0

        activity.append({
            "user_id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "is_active": user.is_active,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "login_count": login_count,
            "contracts_uploaded": contracts_uploaded,
            "analyses_created": analyses_created,
        })

    # Audit log
    audit = AuditLog.create(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.ANALYSIS_EXPORT,
        status=AuditStatus.SUCCESS,
        resource_type="report",
        resource_id="user_activity",
        ip_address=req.client.host if req and req.client else None,
        request_id=req.headers.get("x-request-id"),
    )
    db.add(audit)
    await db.commit()

    return {
        "organization_id": str(current_user.organization_id),
        "period_days": days,
        "users": activity,
    }