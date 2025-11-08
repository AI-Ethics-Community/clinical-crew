"""
FastAPI application and routes.
"""
from app.api.dependencies import get_database, mongodb_client

__all__ = ["get_database", "mongodb_client", "dependencies"]
