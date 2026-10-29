import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

log = logging.getLogger(__name__)


class BaseStore:
    """Shared MongoDB warning behaviour for the individual stores."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._db_warned = False
        self._db_available = True

    def _warn_db(self, err: Exception):
        self._db_available = False
        if not self._db_warned:
            log.warning("MongoDB unavailable (%s) — falling back to in-memory caching", err)
            self._db_warned = True
