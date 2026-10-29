import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.storage.base import BaseStore

log = logging.getLogger(__name__)


class IconStore(BaseStore):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db)
        self.collection = db["icons"]
        self._mem_icons: dict[str, str] = {}
        self._mem_urls: dict[str, str] = {}

    async def save_icon(self, slug: str, icon_uri: str, source_url: str = ""):
        key = slug.strip().lower()
        self._mem_icons[key] = icon_uri
        self._mem_urls[key] = source_url
        try:
            await self.collection.update_one(
                {"_id": key},
                {"$set": {"icon_uri": icon_uri, "source_url": source_url}},
                upsert=True,
            )
            log.info("💾 [Cache SAVED: MongoDB] Icon for %r", key)
        except Exception as e:
            self._warn_db(e)

    async def get_icon(self, slug: str) -> Optional[str]:
        entry = await self.get_icon_entry(slug)
        return entry[0] if entry else None

    async def get_icon_entry(self, slug: str) -> Optional[tuple[str, str]]:
        key = slug.strip().lower()
        if key in self._mem_icons:
            log.info("⚡ [Cache HIT: Memory] Icon for %r", key)
            return self._mem_icons[key], self._mem_urls.get(key, "")
        try:
            doc = await self.collection.find_one({"_id": key})
            if doc:
                icon_uri = doc.get("icon_uri")
                source_url = doc.get("source_url", "")
                if icon_uri:
                    self._mem_icons[key] = icon_uri
                    self._mem_urls[key] = source_url
                    log.info("⚡ [Cache HIT: MongoDB] Icon for %r", key)
                    return icon_uri, source_url
        except Exception as e:
            self._warn_db(e)
        return None

    async def delete_icon(self, slug: str):
        key = slug.strip().lower()
        self._mem_icons.pop(key, None)
        self._mem_urls.pop(key, None)
        try:
            await self.collection.delete_one({"_id": key})
        except Exception as e:
            self._warn_db(e)

    async def clear(self):
        self._mem_icons.clear()
        self._mem_urls.clear()
        try:
            await self.collection.drop()
        except Exception as e:
            self._warn_db(e)
