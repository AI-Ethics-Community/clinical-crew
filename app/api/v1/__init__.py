"""
API v1 endpoints.
"""
from fastapi import APIRouter
from app.api.v1 import consultations

# Create API router
api_router = APIRouter()

# Include routers
api_router.include_router(
    consultations.router,
    tags=["consultations"]
)

__all__ = ["api_router"]
