import base64
import struct

import pytest

from app.processor import ImageProcessor
from app.storage import DepsDB


class TestDepsDB:
    @pytest.mark.anyio
    async def test_deps_db_source_url_tracking(self):
        db = DepsDB()
        await db.save_icon("test-tech", "data:image/png;base64,BBB", source_url="https://example.com/logo.png")
        entry = await db.get_icon_entry("test-tech")
        assert entry is not None
        icon, source_url = entry
        assert icon == "data:image/png;base64,BBB"
        assert source_url == "https://example.com/logo.png"

        # Backwards compatible get_icon
        cached_icon = await db.get_icon("test-tech")
        assert cached_icon == "data:image/png;base64,BBB"


class TestDBCache:
    @pytest.mark.anyio
    async def test_db_cache_evicts_invalid_banner(self):
        from app.sources.dbcache import DBCache

        db = DepsDB()
        proc = ImageProcessor()
        db_cache = DBCache(cache=db, processor=proc)

        # Create a 1280x640 banner data URI
        banner_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", 1280, 640) + b"\x08\x06\x00\x00\x00" + (b"\x00" * 30)
        banner_uri = f"data:image/png;base64,{base64.b64encode(banner_bytes).decode()}"

        await db.save_icon("test-banner-pkg", banner_uri, source_url="https://example.com/banner.png")
        # DBCache should validate and reject the banner, returning None
        res = await db_cache.resolve("test-banner-pkg")
        assert res is None
