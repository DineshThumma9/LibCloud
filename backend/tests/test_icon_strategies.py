from unittest.mock import AsyncMock

import httpx
import pytest

from app.processor import ImageProcessor
from app.sources.favicon import FaviconStrategy
from app.sources.github import HeuristicStrategy
from tests.helpers import make_png


class TestFaviconStrategy:
    @pytest.mark.anyio
    async def test_bs4_favicon_strategy_extracts_brand_svg(self, monkeypatch):
        html_sample = """
        <html>
            <head>
                <link rel="icon" type="image/svg+xml" href="/brand-icon.svg">
            </head>
            <body>
                <a class="navbar-brand" href="/"><img src="/static/img/brand-logo.svg" alt="Brand Logo"></a>
            </body>
        </html>
        """
        svg_bytes = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/></svg>'

        class MockResponse:
            def __init__(self, text="", content=b"", status_code=200, url="https://example.com/"):
                self.text = text
                self.content = content
                self.status_code = status_code
                self.url = httpx.URL(url)
                self.headers = {"content-type": "image/svg+xml" if content else "text/html"}

        async def mock_get(client, url, *args, **kwargs):
            url_str = str(url)
            if url_str in ("https://example.com/", "https://example.com"):
                return MockResponse(text=html_sample, status_code=200, url="https://example.com/")
            if "brand-logo.svg" in url_str:
                return MockResponse(content=svg_bytes, status_code=200, url=url_str)
            return MockResponse(status_code=404)

        async with httpx.AsyncClient() as client:
            monkeypatch.setattr(client, "get", lambda *a, **kw: mock_get(client, *a, **kw))
            proc = ImageProcessor()
            fav = FaviconStrategy(client, proc)
            res = await fav.resolve_domain("example.com", "example-pkg")
            assert res is not None
            icon_uri, method, source_url = res
            assert method == "homepage_favicon"
            assert "brand-logo.svg" in source_url
            assert icon_uri.startswith("data:image/svg+xml;base64,")


class TestGithubDefaultAvatar:
    @pytest.mark.anyio
    async def test_default_org_avatar_is_skipped(self, monkeypatch):
        rows = [[255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255]] * 4
        avatar = make_png(4, 4, rows, 0)
        identicon = make_png(4, 4, rows, 2)

        class MockResponse:
            def __init__(self, content):
                self.content = content
                self.status_code = 200
                self.headers = {"content-type": "image/png"}

        async def mock_get(client, url, *args, **kwargs):
            return MockResponse(identicon if "identicons" in str(url) else avatar)

        async with httpx.AsyncClient() as client:
            monkeypatch.setattr(client, "get", lambda *a, **kw: mock_get(client, *a, **kw))
            strategy = HeuristicStrategy(client, ImageProcessor())
            strategy._is_github_org = AsyncMock(return_value=True)
            assert await strategy.resolve_avatar("example-org", "example-pkg") is None

    @pytest.mark.anyio
    async def test_custom_org_avatar_is_kept(self, monkeypatch):
        avatar_rows = [[255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255]] * 4
        identicon_rows = [[0, 0, 255, 255, 255, 0, 0, 255, 0, 255, 0, 255]] * 4
        avatar = make_png(4, 4, avatar_rows, 0)
        identicon = make_png(4, 4, identicon_rows, 0)

        class MockResponse:
            def __init__(self, content):
                self.content = content
                self.status_code = 200
                self.headers = {"content-type": "image/png"}

        async def mock_get(client, url, *args, **kwargs):
            return MockResponse(identicon if "identicons" in str(url) else avatar)

        async with httpx.AsyncClient() as client:
            monkeypatch.setattr(client, "get", lambda *a, **kw: mock_get(client, *a, **kw))
            strategy = HeuristicStrategy(client, ImageProcessor())
            strategy._is_github_org = AsyncMock(return_value=True)
            res = await strategy.resolve_avatar("example-org", "example-pkg")

        assert res is not None
        assert res[1] == "github_org_avatar"

    @pytest.mark.anyio
    async def test_unverifiable_org_avatar_is_skipped(self, monkeypatch):
        avatar = make_png(4, 4, [[255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255]] * 4, 0)

        class MockResponse:
            def __init__(self, content=b"", status_code=200):
                self.content = content
                self.status_code = status_code
                self.headers = {"content-type": "image/png"}

        async def mock_get(client, url, *args, **kwargs):
            if "identicons" in str(url):
                return MockResponse(status_code=404)
            return MockResponse(content=avatar)

        async with httpx.AsyncClient() as client:
            monkeypatch.setattr(client, "get", lambda *a, **kw: mock_get(client, *a, **kw))
            strategy = HeuristicStrategy(client, ImageProcessor())
            strategy._is_github_org = AsyncMock(return_value=True)
            assert await strategy.resolve_avatar("example-org", "example-pkg") is None
