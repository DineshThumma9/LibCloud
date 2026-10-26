import base64
import logging
from typing import Optional
from storage import DepsDB
from processor import ImageProcessor

log = logging.getLogger(__name__)


class DBCache:
    def __init__(self, cache: Optional[DepsDB] = None, processor: Optional[ImageProcessor] = None):
        self.cache = cache if cache is not None else DepsDB()
        self.processor = processor

    async def resolve(self, slug: str) -> Optional[tuple[str, str, str]]:
        entry = await self.cache.get_icon_entry(slug)
        if entry:
            icon, source_url = entry
            if self.processor and icon:
                try:
                    raw = None
                    if icon.startswith("data:"):
                        _, b64data = icon.split(",", 1)
                        raw = base64.b64decode(b64data)
                    if raw:
                        val = self.processor.validate_image(raw)
                        if not val.is_valid:
                            key = slug.strip().lower()
                            log.warning("Evicting invalid cached icon for %r: %s", key, val.reason)
                            self.cache._mem_icons.pop(key, None)
                            self.cache._mem_urls.pop(key, None)
                            try:
                                await self.cache.icons.delete_one({"_id": key})
                            except Exception:
                                pass
                            return None
                except Exception:
                    pass
            return icon, "db_cache", source_url or "db_cache"
        return None
