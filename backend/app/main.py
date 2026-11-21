"""ContractAI FastAPI application entry point."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone

from app.api.v1.router import api_router
from app.config import get_settings
from app.database import close_db, check_db_connection, init_db, get_db
from app.schemas.common import ErrorResponse, HealthCheckResponse
from app.services.auth import get_current_user_dependency
from app.services.llm_client import close_llm_client, get_llm_client

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    # Startup
    # Initialize LLM client
    get_llm_client()
    # Initialize database (development only - production uses migrations)
    await init_db()
    yield
    # Shutdown
    await close_llm_client()
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    description="ContractAI - Intelligent Contract Analysis Platform",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=(settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list)
                   else settings.cors_origins_list),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
if settings.PROMETHEUS_METRICS_ENABLED:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


# Exception handlers
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="database_error",
            message="A database error occurred",
            details=[{"code": "DB_ERROR", "message": str(exc)}],
            request_id=request.headers.get("x-request-id"),
        ).model_dump(mode="json"),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="validation_error",
            message=str(exc),
            details=[{"code": "VALIDATION_ERROR", "message": str(exc)}],
            request_id=request.headers.get("x-request-id"),
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="internal_server_error",
            message="An unexpected error occurred" if not settings.DEBUG else str(exc),
            details=[{"code": "INTERNAL_ERROR", "message": str(exc)}] if settings.DEBUG else [],
            request_id=request.headers.get("x-request-id"),
        ).model_dump(mode="json"),
    )


# LGPD Compliance Endpoints
@app.post(
    "/api/v1/auth/data/export",
    response_model=dict,
    summary="Export all user data (LGPD Art. 18)",
    tags=["LGPD"],
)
async def export_user_data(
    request: Request,
    db=Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    """Export all personal data for the authenticated user (LGPD Right to Access)."""
    from app.models.user import User
    from app.models.contract import Contract
    from app.models.analysis import Analysis
    from app.models.clause import Clause
    from app.models.audit_log import AuditLog
    from app.models.connector import Connector
    from sqlalchemy import select

    user_id = current_user.id
    org_id = current_user.organization_id

    # Collect all user data
    user_data = {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "mfa_enabled": current_user.mfa_enabled,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
            "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
        },
        "contracts": [],
        "analyses": [],
        "clauses": [],
        "audit_logs": [],
        "connectors": [],
    }

    # Contracts
    contracts_result = await db.execute(
        select(Contract).where(Contract.owner_id == user_id, Contract.deleted_at.is_(None))
    )
    for contract in contracts_result.scalars().all():
        user_data["contracts"].append({
            "id": str(contract.id),
            "title": contract.title,
            "source": contract.source,
            "status": contract.status,
            "page_count": contract.page_count,
            "language": contract.language,
            "created_at": contract.created_at.isoformat() if contract.created_at else None,
            "updated_at": contract.updated_at.isoformat() if contract.updated_at else None,
        })

    # Analyses
    analyses_result = await db.execute(
        select(Analysis).where(Analysis.created_by_id == user_id, Analysis.deleted_at.is_(None))
    )
    for analysis in analyses_result.scalars().all():
        user_data["analyses"].append({
            "id": str(analysis.id),
            "contract_id": str(analysis.contract_id),
            "type": analysis.type,
            "status": analysis.status,
            "llm_provider": analysis.llm_provider,
            "llm_model": analysis.llm_model,
            "result": analysis.result,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
            "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        })

    # Clauses
    clauses_result = await db.execute(
        select(Clause).where(Clause.organization_id == org_id, Clause.deleted_at.is_(None))
    )
    for clause in clauses_result.scalars().all():
        user_data["clauses"].append({
            "id": str(clause.id),
            "analysis_id": str(clause.analysis_id),
            "type": clause.type,
            "content": clause.content,
            "risk_score": clause.risk_score,
            "risk_level": clause.risk_level,
            "entities": clause.entities,
        })

    # Audit logs (last 1000)
    audit_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(1000)
    )
    for audit in audit_result.scalars().all():
        user_data["audit_logs"].append({
            "id": str(audit.id),
            "action": audit.action,
            "resource_type": audit.resource_type,
            "resource_id": audit.resource_id,
            "status": audit.status,
            "details": audit.details,
            "created_at": audit.created_at.isoformat() if audit.created_at else None,
        })

    # Connectors
    connectors_result = await db.execute(
        select(Connector).where(Connector.organization_id == org_id, Connector.deleted_at.is_(None))
    )
    for conn in connectors_result.scalars().all():
        user_data["connectors"].append({
            "id": str(conn.id),
            "name": conn.name,
            "type": conn.type,
            "is_active": conn.is_active,
            "last_sync_at": conn.last_sync_at.isoformat() if conn.last_sync_at else None,
        })

    # Audit the export
    from app.models.audit_log import AuditAction, AuditLog, AuditStatus
    audit = AuditLog.create(
        organization_id=org_id,
        user_id=current_user.id,
        action=AuditAction.DATA_EXPORT_REQUEST,
        status=AuditStatus.SUCCESS,
        details={"data_types": list(user_data.keys())},
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()

    return {
        "message": "Data export completed",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "data": user_data,
    }


@app.post(
    "/api/v1/auth/data/delete",
    response_model=dict,
    summary="Request deletion of all user data (LGPD Art. 18)",
    tags=["LGPD"],
)
async def request_data_deletion(
    request: Request,
    db=Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    """Request deletion of all personal data (LGPD Right to Deletion)."""
    from app.models.audit_log import AuditAction, AuditLog, AuditStatus

    user_id = current_user.id
    org_id = current_user.organization_id

    # In production, this would trigger an async job to:
    # 1. Soft delete user data
    # 2. Anonymize data if ANONYMIZE_ON_DELETE=True
    # 2. Remove from backups within retention period
    # 4. Notify user when complete

    # For now, we just audit the request
    audit = AuditLog.create(
        organization_id=org_id,
        user_id=user_id,
        action=AuditAction.DATA_DELETION_REQUEST,
        status=AuditStatus.SUCCESS,
        details={"requested_by_user": True},
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()

    return {
        "message": "Data deletion request received. Your data will be processed according to LGPD requirements.",
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "estimated_completion": "Within 15 business days",
    }


# Health check endpoints
@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check() -> HealthCheckResponse:
    """Basic health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        environment=settings.APP_ENV,
    )


@app.get("/health/ready", response_model=HealthCheckResponse, tags=["Health"])
async def readiness_check() -> HealthCheckResponse:
    """Readiness check with dependency verification (no Redis required)."""
    from app.database import check_db_connection

    checks = {}
    overall_status = "healthy"

    # Check database
    db_ok = await check_db_connection()
    checks["database"] = "connected" if db_ok else "error"
    if not db_ok:
        overall_status = "unhealthy"

    # Check LLM providers
    llm_client = get_llm_client()
    available = llm_client.available_providers
    checks["llm_providers"] = available
    if not available:
        overall_status = "degraded"

    return HealthCheckResponse(
        status=overall_status,
        version="1.0.0",
        environment=settings.APP_ENV,
        checks=checks,
    )


# API routes
app.include_router(api_router, prefix="/api/v1")

# Root endpoint
@app.get("/", include_in_schema=False)
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "description": "ContractAI - Intelligent Contract Analysis Platform",
        "docs": "/docs" if settings.DEBUG else "disabled",
        "health": "/health",
    }