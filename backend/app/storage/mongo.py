from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

_shared_client: Optional[AsyncIOMotorClient] = None


def get_client(uri: Optional[str] = None) -> AsyncIOMotorClient:
    """Return a dedicated client for an explicit URI, otherwise one shared client."""
    global _shared_client
    if uri:
        return AsyncIOMotorClient(uri, serverSelectionTimeoutMS=2000)
    if _shared_client is None:
        _shared_client = AsyncIOMotorClient(settings.get_mongo_uri(), serverSelectionTimeoutMS=2000)
    return _shared_client
