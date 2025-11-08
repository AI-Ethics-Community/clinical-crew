"""
FastAPI dependencies.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings

# MongoDB client (will be initialized in main.py)
mongodb_client: AsyncIOMotorClient = None


def get_database():
    """
    Get MongoDB database instance.

    Returns:
        Database instance
    """
    return mongodb_client[settings.mongodb_db_name]
