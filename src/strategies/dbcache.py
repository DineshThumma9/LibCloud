from typing import Optional
from storage import DepsDB


class DBCache:
    def __init__(self, cache: Optional[DepsDB] = None):
        self.cache = cache if cache is not None else DepsDB()

    async def resolve(self, slug: str) -> Optional[tuple[str, str, str]]:
        entry = await self.cache.get_icon_entry(slug)
        if entry:
            icon, source_url = entry
            return icon, "db_cache", source_url or "db_cache"
        return None
