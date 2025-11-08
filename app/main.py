"""
Clinical Crew - Main FastAPI Application
Multi-agent medical consultation system with RAG and LangGraph
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from app.config.settings import settings
from app.models.database import init_db
from app.api import dependencies
from app.api.v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    print("🚀 Starting Clinical Crew...")

    # Initialize MongoDB connection
    print(f"📊 Connecting to MongoDB: {settings.mongodb_url}")
    dependencies.mongodb_client = AsyncIOMotorClient(
        settings.mongodb_url,
        maxPoolSize=settings.mongodb_max_connections,
        minPoolSize=settings.mongodb_min_connections,
    )

    # Initialize Beanie
    database = dependencies.mongodb_client[settings.mongodb_db_name]
    await init_db(database)
    print("✓ MongoDB connected and Beanie initialized")

    # Verify ChromaDB directory exists
    import os

    os.makedirs(settings.chroma_persist_directory, exist_ok=True)
    print(f"✓ ChromaDB directory ready: {settings.chroma_persist_directory}")

    print("✅ Application started successfully!")

    yield

    # Shutdown
    print("🛑 Shutting down Clinical Crew...")

    # Close MongoDB connection
    if dependencies.mongodb_client:
        dependencies.mongodb_client.close()
        print("✓ MongoDB connection closed")

    print("👋 Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.api_v1_prefix)


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        System health status
    """
    return {
        "status": "healthy",
        "service": "Clinical Crew",
        "version": settings.api_version,
    }


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint with API information.

    Returns:
        API information
    """
    return {
        "service": "Clinical Crew",
        "description": "Multi-agent medical consultation system",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
