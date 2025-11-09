"""
API v1 endpoints.
"""
from fastapi import APIRouter
from app.api.v1 import consultations, websockets

api_router = APIRouter()

api_router.include_router(
    consultations.router,
    tags=["consultations"]
)

api_router.include_router(
    websockets.router,
    tags=["websockets"]
)

__all__ = ["api_router"]
