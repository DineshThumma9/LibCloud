from functools import lru_cache

from app.storage import DepsDB


@lru_cache
def get_db() -> DepsDB:
    """One cache/store instance per process, created on first use."""
    return DepsDB()
