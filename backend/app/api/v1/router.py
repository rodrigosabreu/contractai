"""API v1 router aggregating all endpoints."""
from fastapi import APIRouter

from app.api.v1 import auth, contracts, analysis, reports, connectors, organizations, users, clauses

api_router = APIRouter()

# Authentication
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Users
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# Organizations
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])

# Contracts
api_router.include_router(contracts.router, prefix="/contracts", tags=["Contracts"])

# Analysis
api_router.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])

# Clauses
api_router.include_router(clauses.router, prefix="/clauses", tags=["Clauses"])

# Reports
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])

# Connectors
api_router.include_router(connectors.router, prefix="/connectors", tags=["Connectors"])