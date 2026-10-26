import pytest
import struct
import zlib
from pathlib import Path
import sys

# Ensure src is in sys.path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from models import ProjectLinks
from processor import ImageProcessor
from parser import parse_pipfile, parse_workflow, DependencyParser
from constants import SLUG_MAP, NORM


def _make_png(width, height, rows, filter_type=0):
    prev = bytes(width * 3)
    raw = b""
    for row in rows:
        current = bytes(row)
        if filter_type == 2:
            current = bytes((value - up) & 255 for value, up in zip(current, prev))
        raw += bytes([filter_type]) + current
        prev = bytes(row)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


class TestImageValidation:
    def test_svg_with_xml_prolog(self):
        svg_content = b'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/></svg>'
        valid, reason = ImageProcessor.validate_image(svg_content)
        assert valid is True
        assert reason == "valid_svg"

    def test_svg_with_long_header(self):
        long_comment = b"<!-- " + (b"A" * 200) + b" -->\n"
        svg_content = long_comment + b'<svg viewBox="0 0 100 100"><rect width="10" height="10"/></svg>'
        valid, reason = ImageProcessor.validate_image(svg_content)
        assert valid is True
        assert reason == "valid_svg"

    def test_reject_html_page(self):
        html_content = b"<!DOCTYPE html><html><head><title>404 Not Found</title></head><body>Error</body></html>"
        valid, reason = ImageProcessor.validate_image(html_content)
        assert valid is False
        assert reason == "is_html_page_not_image"

    def test_reject_tracking_pixel(self):
        # 1x1 PNG header
        png_1x1 = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", 1, 1) + b"\x08\x06\x00\x00\x00" + (b"\x00" * 30)
        valid, reason = ImageProcessor.validate_image(png_1x1)
        assert valid is False
        assert "rejected_tracking_pixel" in reason

    def test_valid_png(self):
        png_32x32 = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", 32, 32) + b"\x08\x06\x00\x00\x00" + (b"\x00" * 30)
        valid, reason = ImageProcessor.validate_image(png_32x32)
        assert valid is True
        assert "valid_png" in reason

    def test_svg_content_is_preserved(self):
        import base64
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10" fill="#fff"></rect><path fill="#010101" d="M0 0h10v10z"/></svg>'
        uri = ImageProcessor().to_data_uri(svg, "image/svg+xml")
        decoded = base64.b64decode(uri.split(",", 1)[1]).decode("utf-8")
        assert 'fill="#010101"' in decoded
        assert 'fill="#fff"' in decoded


class TestProjectLinksURLParsing:
    def test_owner_only_github_url(self):
        links = ProjectLinks.parse_urls_to_links(["https://github.com/psf"])
        assert links.github_owner == "psf"
        assert links.github_repo is None

    def test_owner_repo_github_url(self):
        links = ProjectLinks.parse_urls_to_links(["https://github.com/psf/requests.git"])
        assert links.github_owner == "psf"
        assert links.github_repo == "requests"

    def test_sponsors_github_url(self):
        links = ProjectLinks.parse_urls_to_links(["https://github.com/sponsors/pallets"])
        assert links.github_owner == "pallets"
        assert links.github_repo is None

    def test_non_github_host_rejection(self):
        links = ProjectLinks.parse_urls_to_links([
            "https://notgithub.com/owner/repo",
            "https://github.com.evil.com/owner/repo",
        ])
        assert links.github_owner is None
        assert links.github_repo is None


class TestPipfileParser:
    def test_parse_pipfile_ignores_metadata(self):
        content = """
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
requests = "*"
fastapi = ">=0.100.0"

[dev-packages]
pytest = ">=7.0"

[requires]
python_version = "3.11"
"""
        deps = parse_pipfile(content)
        assert "requests" in deps
        assert "fastapi" in deps
        assert "pytest" in deps
        assert "python_version" not in deps


class TestWorkflowParser:
    def test_parse_workflow_actions(self):
        content = """
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v2
      - uses: appleboy/ssh-action@v0.1.10
"""
        raws = parse_workflow(content)
        assert "actions/checkout@v4" in raws
        assert "docker/setup-buildx-action@v2" in raws
        assert "appleboy/ssh-action@v0.1.10" in raws

        parser = DependencyParser()
        pkg_dic = parser.parser(content, ".github/workflows/ci.yml")
        assert "GitHub Actions" in pkg_dic
        assert "Docker" in pkg_dic
        assert "appleboy/ssh-action" in pkg_dic


class TestCacheKeyConsistency:
    def test_cache_keys_match(self):
        for tech in ["GitHub Actions", "PostgreSQL", "ChromaDB", "Pinecone"]:
            slug = SLUG_MAP.get(tech, tech).lower()
            assert slug.islower()
            assert not slug.startswith(" ")


class TestConstantsFixes:
    def test_slug_map_brand_corrections(self):
        assert SLUG_MAP["OkHttp"] == "square"
        assert SLUG_MAP["Google Gemini"] == "googlegemini"
        assert SLUG_MAP["Radix UI"] == "radixui"
        assert SLUG_MAP["Werkzeug"].endswith("werkzeug-icon.svg")
        assert SLUG_MAP["Node.js"] == "nodedotjs"
        assert SLUG_MAP["HeroUI"] == "heroui"
        assert "Tabler Icons" not in SLUG_MAP
        assert "Nomic Foundation" not in SLUG_MAP

    def test_go_subpackage_noise_filtering(self):
        parser = DependencyParser()
        res, lang = parser.normalize_pkg("github.com/stretchr/testify/assert", "go.mod")
        assert res is None and lang is None

        res, lang = parser.normalize_pkg("github.com/stretchr/testify/require", "go.mod")
        assert res is None and lang is None

    def test_next_themes_normalization(self):
        parser = DependencyParser()
        res, lang = parser.normalize_pkg("next-themes", "package.json")
        assert res == "Next.js"
        assert lang == "ts"

    def test_neondatabase_normalization(self):
        parser = DependencyParser()
        res, lang = parser.normalize_pkg("@neondatabase/serverless", "package.json")
        assert res == "PostgreSQL"
        assert lang == "ts"

    def test_elasticsearch_java_normalization(self):
        parser = DependencyParser()
        res, lang = parser.normalize_pkg("co.elastic.clients:elasticsearch-java", "pom.xml")
        assert res == "Elasticsearch"
        assert lang == "java"

    def test_neo4j_casing_consistency(self):
        parser = DependencyParser()
        res, lang = parser.normalize_pkg("langchain-neo4j", "pyproject.toml")
        assert res == "Neo4j"
        assert lang == "py"

    def test_kotlin_jpa_consistency(self):
        parser = DependencyParser()
        res, lang = parser.normalize_pkg("spring-boot-starter-data-jpa", "build.gradle.kts")
        assert res == "JPA / Hibernate"
        assert lang == "kotlin"


class TestModelsAndAPIHelpers:
    def test_pkginfo_merge(self):
        from models import PKGInfo, merge_pkg_dicts
        p1 = PKGInfo(count=2, dep_origin="py", raw_names={"requests"})
        p2 = PKGInfo(count=3, dep_origin="py", raw_names={"requests-oauth"})
        p1.merge(p2)
        assert p1.count == 5
        assert p1.dep_origin == "py"
        assert p1.raw_names == {"requests", "requests-oauth"}

        target = {"FastAPI": PKGInfo(count=1, dep_origin="py", raw_names={"fastapi"})}
        source = {"FastAPI": PKGInfo(count=2, dep_origin="py", raw_names={"fastapi"}), "Docker": PKGInfo(count=1, dep_origin="docker", raw_names={"docker"})}
        merge_pkg_dicts(target, source)
        assert target["FastAPI"].count == 3
        assert target["Docker"].count == 1

    def test_validation_result_unpacking_and_attributes(self):
        from processor import ValidationResult
        res = ValidationResult(True, "valid_svg", "image/svg+xml")
        valid, reason = res
        assert valid is True
        assert reason == "valid_svg"
        assert res.mime_type == "image/svg+xml"

    def test_graph_github_api_lifecycle(self):
        from api import GraphGithubAPI
        api = GraphGithubAPI("test_user", token="ghp_test123")
        assert api.token_exists is True
        api_no_token = GraphGithubAPI("test_user")
        assert api_no_token.token_exists is False


class TestIconMappingAudit:
    def test_output_csv_includes_source_url(self, tmp_path):
        from ops_logger import DepOpsLogger
        import csv
        csv_path = tmp_path / "output.csv"
        logger = DepOpsLogger(output_path=str(csv_path))
        badge_items = [("FastAPI", "data:image/svg+xml;base64,AAA", 5)]
        methods = {"FastAPI": "cdn_catalog"}
        urls = {"FastAPI": "https://cdn.simpleicons.org/fastapi"}
        logger.export_output_csv(badge_items, methods, urls)

        with csv_path.open() as f:
            reader = list(csv.reader(f))
            assert reader[0] == ["technology", "count", "resolution_method", "source_url"]
            assert reader[1] == ["FastAPI", "5", "cdn_catalog", "https://cdn.simpleicons.org/fastapi"]

    def test_export_audit_html_renders_visual_table(self, tmp_path):
        from ops_logger import DepOpsLogger
        html_path = tmp_path / "icon_audit.html"
        logger = DepOpsLogger()
        badge_items = [("FastAPI", "data:image/svg+xml;base64,AAA", 5)]
        methods = {"FastAPI": "cdn_catalog"}
        urls = {"FastAPI": "https://cdn.simpleicons.org/fastapi"}
        logger.export_audit_html(badge_items, methods, urls, filepath=str(html_path))

        assert html_path.exists()
        content = html_path.read_text(encoding="utf-8")
        assert "FastAPI" in content
        assert "https://cdn.simpleicons.org/fastapi" in content
        assert "cdn_catalog" in content
        assert "data:image/svg+xml;base64,AAA" in content

    @pytest.mark.anyio
    async def test_deps_db_source_url_tracking(self):
        from storage import DepsDB
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

    def test_reject_widescreen_banner(self):
        from processor import ImageProcessor
        import struct
        # 1200x630 banner
        banner_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", 1200, 630) + b"\x08\x06\x00\x00\x00" + (b"\x00" * 30)
        valid, reason = ImageProcessor.validate_image(banner_bytes)
        assert valid is False
        assert "rejected_banner_aspect_ratio" in reason

    def test_new_technology_normalizations(self):
        from parser import DependencyParser
        parser = DependencyParser()

        cases = [
            ("langchain-checkpoint-postgres", "pyproject.toml", "PostgreSQL", "py"),
            ("langchain-redis", "pyproject.toml", "Redis", "py"),
            ("langchain-mcp-adapters", "pyproject.toml", "MCP", "py"),
            ("mcp-server-qdrant", "pyproject.toml", "Qdrant", "py"),
            ("mcp", "pyproject.toml", "FastMCP", "py"),
            ("sse-starlette", "pyproject.toml", "Starlette", "py"),
            ("uvloop", "pyproject.toml", "libuv", "py"),
            ("python-jose", "pyproject.toml", "JWT", "py"),
            ("beautifulsoup4", "pyproject.toml", "Beautiful Soup", "py"),
            ("sockjs-client", "package.json", "SockJS", "ts"),
            ("astryxdesign", "package.json", "Astryx", "ts"),
            ("reportlab", "requirements.txt", "ReportLab", "py"),
            ("tf_keras", "requirements.txt", "Keras", "py"),
            ("tf-keras", "requirements.txt", "Keras", "py"),
            ("urllib3", "requirements.txt", "urllib3", "py"),
            ("@uiw/react-codemirror", "package.json", "CodeMirror", "ts"),
            ("jspdf-autotable", "package.json", "jsPDF", "ts"),
            ("jspdf", "package.json", "jsPDF", "ts"),
            ("postcss", "package.json", "PostCSS", "ts"),
            ("oxlint", "package.json", "Oxlint", "ts"),
            ("djangorestframework", "requirements.txt", "Django", "py"),
            ("pyjwt", "requirements.txt", "JWT", "py"),
            ("moviepy", "requirements.txt", "MoviePy", "py"),
            ("react-native-safe-area-context", "package.json", "React Native", "ts"),
            ("react-native-screens", "package.json", "React Native", "ts"),
            ("react-native-svg", "package.json", "React Native", "ts"),
            ("react-native-web", "package.json", "React Native", "ts"),
            ("eslint-plugin-react", "package.json", "ESLint", "ts"),
            ("eslint-plugin-turbo", "package.json", "ESLint", "ts"),
            ("softprops/action-gh-release", ".github/workflows/deploy.yml", "GitHub Actions", "actions"),
            ("golangci/golangci-lint-action", ".github/workflows/lint.yml", "GitHub Actions", "actions"),
            ("volley", "pom.xml", "Android", "java"),
            ("android-sdk", "pom.xml", "Android", "java"),
            ("solana-sdk", "Cargo.toml", "Solana", "rust"),
            ("solana-program", "Cargo.toml", "Solana", "rust"),
            ("solana-client", "Cargo.toml", "Solana", "rust"),
            ("solana-rpc-client", "Cargo.toml", "Solana", "rust"),
            ("@solana/web3.js", "package.json", "Solana", "ts"),
            ("@solana/spl-token", "package.json", "Solana", "ts"),
            ("@solana-developers/helpers", "package.json", "Solana", "ts"),
            ("eslint-plugin-jsx-a11y", "package.json", "ESLint", "ts"),
            ("react-native-gesture-handler", "package.json", "React Native", "ts"),
            ("ts-mocha", "package.json", "Mocha", "ts"),
            ("hardhat-gas-reporter", "package.json", "Hardhat", "ts"),
            ("vite-plugin-node-polyfills", "package.json", "Vite", "ts"),
            ("react-lottie", "package.json", "Lottie", "ts"),
            ("connect-mongo", "package.json", "MongoDB", "ts"),
            ("multer-storage-cloudinary", "package.json", "Cloudinary", "ts"),
            ("react-spotify-embed", "package.json", "Spotify", "ts"),
            ("react-github-calendar", "package.json", "GitHub", "ts"),
            ("redux-persist", "package.json", "Redux", "ts"),
            ("next-pwa", "package.json", "Next.js", "ts"),
            ("bcrypt-ts", "package.json", "Bcrypt", "ts"),
            ("serde-wasm-bindgen", "Cargo.toml", "Serde", "rust"),
            ("connect-flash", "package.json", "Express", "ts"),
            ("cookieparser", "package.json", "Express", "ts"),
            ("ejs-mate", "package.json", "Express", "ts"),
            ("request-ip", "package.json", "Express", "ts"),
            ("passport-local-mongoose", "package.json", "MongoDB", "ts"),
            ("react-confetti", "package.json", "React", "ts"),
            ("react-cool-inview", "package.json", "React", "ts"),
            ("use-sound", "package.json", "React", "ts"),
            ("react-chartjs-2", "package.json", "Chart.js", "ts"),
            ("werkzeug", "requirements.txt", "Werkzeug", "py"),
            ("multer", "package.json", "Express", "ts"),
            ("method-override", "package.json", "Express", "ts"),
            ("fs", "package.json", "Node.js", "ts"),
            ("expo-constants", "package.json", "Expo", "ts"),
            ("@nextui-org/react", "package.json", "HeroUI", "ts"),
            ("@nomiclabs/hardhat-ethers", "package.json", "nomiclabs", "ts"),
            ("@nomicfoundation/hardhat-ethers", "package.json", "nomiclabs", "ts"),
            ("@tabler/icons-react", "package.json", "Tabler Icons", "ts"),
        ]

        for raw, fname, expected_norm, expected_lang in cases:
            norm, lang = parser.normalize_pkg(raw, fname)
            assert norm == expected_norm, f"Expected {raw} -> {expected_norm}, got {norm}"
            assert lang == expected_lang

    def test_noise_filtering(self):
        from parser import DependencyParser
        parser = DependencyParser()
        noise_samples = [
            ("cors", "package.json"),
            ("cros", "package.json"),
            ("bun-plugin-tailwind", "package.json"),
            ("husky", "package.json"),
            ("cors", "requirements.txt"),
            ("install", "package.json"),
            ("glob", "package.json"),
            ("tls", "package.json"),
            ("db", "package.json"),
            ("simple_asn1", "Cargo.toml"),
            ("zkpdf-lib", "Cargo.toml"),
            ("github.com/peterh/liner", "go.mod"),
            ("github.com/mattn/go-runewidth", "go.mod"),
        ]
        for raw, fname in noise_samples:
            norm, lang = parser.normalize_pkg(raw, fname)
            assert norm is None, f"Expected {raw} in {fname} to be filtered as noise, got {norm}"

    @pytest.mark.anyio
    async def test_db_cache_evicts_invalid_banner(self):
        import base64
        import struct
        from storage import DepsDB
        from processor import ImageProcessor
        from strategies.dbcache import DBCache

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

    @pytest.mark.anyio
    async def test_bs4_favicon_strategy_extracts_brand_svg(self, monkeypatch):
        import httpx
        from processor import ImageProcessor
        from strategies.favicon import FaviconStrategy

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


class TestDependencyGraphLockfiles:
    @pytest.mark.anyio
    async def test_lockfile_manifests_are_skipped(self):
        from unittest.mock import AsyncMock
        from api import GraphGithubAPI

        api = GraphGithubAPI("test_user")
        api.dep_db.get_repo_deps = AsyncMock(return_value=None)
        api.dep_db.save_repo_deps = AsyncMock()

        async def fake_execute(*args, **kwargs):
            return {
                "repository": {
                    "dependencyGraphManifests": {
                        "nodes": [
                            {"filename": "Cargo.lock", "dependencies": {"nodes": [{"packageName": "bytemuck"}]}},
                            {"filename": "package-lock.json", "dependencies": {"nodes": [{"packageName": "left-pad"}]}},
                            {"filename": "Cargo.toml", "dependencies": {"nodes": [{"packageName": "serde"}]}},
                            {"filename": "package.json", "dependencies": {"nodes": [{"packageName": "react"}]}},
                        ]
                    }
                }
            }

        api.ghc.execute = fake_execute
        try:
            pkg_dic = await api.fetch_repo_deps("test-repo")
        finally:
            await api.aclose()

        assert "Serde" in pkg_dic
        assert "React" in pkg_dic
        assert "bytemuck" not in pkg_dic
        assert "left-pad" not in pkg_dic


class TestActionsFallback:
    @pytest.mark.anyio
    async def test_action_owner_avatar_fallback(self):
        from unittest.mock import AsyncMock
        from resolver import ImageResolver

        resolver = ImageResolver(github_token=None)
        resolver.db_cache.resolve = AsyncMock(return_value=None)
        resolver.github.resolve = AsyncMock(return_value=None)
        avatar = ("data:image/png;base64,AAA", "github_org_avatar", "https://github.com/foundry-rs.png")
        resolver.github.resolve_avatar = AsyncMock(return_value=avatar)
        try:
            res = await resolver.resolve_package(
                "foundry-rs/foundry-toolchain@v1", "actions", "foundry-rs/foundry-toolchain"
            )
        finally:
            await resolver.aclose()

        assert res == avatar
        resolver.github.resolve.assert_awaited_once_with(
            "foundry-rs", "foundry-toolchain", "foundry-rs/foundry-toolchain@v1"
        )
        resolver.github.resolve_avatar.assert_awaited_once_with(
            "foundry-rs", "foundry-rs/foundry-toolchain@v1"
        )


class TestGithubDefaultAvatar:
    def test_same_pixels_with_different_png_filters(self):
        rows = [[255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255]] * 4
        a = _make_png(4, 4, rows, 0)
        b = _make_png(4, 4, rows, 2)
        changed = [[0, 0, 255, 255, 255, 0, 0, 255, 0, 255, 0, 255]] * 4

        assert a != b
        assert ImageProcessor.same_pixels(a, b) is True
        assert ImageProcessor.same_pixels(a, _make_png(4, 4, changed, 0)) is False

    @pytest.mark.anyio
    async def test_default_org_avatar_is_skipped(self, monkeypatch):
        import httpx
        from unittest.mock import AsyncMock
        from strategies.github import HeuristicStrategy

        rows = [[255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255]] * 4
        avatar = _make_png(4, 4, rows, 0)
        identicon = _make_png(4, 4, rows, 2)

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
        import httpx
        from unittest.mock import AsyncMock
        from strategies.github import HeuristicStrategy

        avatar_rows = [[255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255]] * 4
        identicon_rows = [[0, 0, 255, 255, 255, 0, 0, 255, 0, 255, 0, 255]] * 4
        avatar = _make_png(4, 4, avatar_rows, 0)
        identicon = _make_png(4, 4, identicon_rows, 0)

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
        import httpx
        from unittest.mock import AsyncMock
        from strategies.github import HeuristicStrategy

        avatar = _make_png(4, 4, [[255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255]] * 4, 0)

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


class TestWordcloudSvg:
    def test_empty_input_uses_preset_dimensions(self):
        from utils import transform_wordcloud
        svg = transform_wordcloud({}, preset="readme")
        assert 'width="920"' in svg
        assert 'height="540"' in svg

    def test_max_logos_keeps_highest_counts(self):
        from utils import transform_wordcloud
        badges = [
            ("A", "data:image/png;base64,AAA", 10),
            ("B", "data:image/png;base64,BBB", 5),
            ("C", "data:image/png;base64,CCC", 1),
        ]
        svg = transform_wordcloud(badges, preset="web", max_logos=2)
        assert svg.count('class="logo-item"') == 2
        assert "A (10)" in svg
        assert "B (5)" in svg
        assert "C (1)" not in svg

    def test_dark_theme_adds_plates(self):
        from utils import transform_wordcloud
        badges = [("A", "data:image/png;base64,AAA", 1)]
        svg = transform_wordcloud(badges, preset="web", theme="dark")
        assert svg.count('class="logo-plate"') == 1
        assert 'fill="#f1f5f9"' in svg
        assert '<rect width="1400" height="900" rx="16" fill="#1a1b26"' in svg

    def test_light_theme_omits_plates(self):
        from utils import transform_wordcloud
        badges = [("A", "data:image/png;base64,AAA", 1)]
        svg = transform_wordcloud(badges, preset="web", theme="light")
        assert 'class="logo-plate"' not in svg
        assert '<rect width="1400" height="900" rx="16" fill="#ffffff"' in svg

    def test_theme_inferred_from_light_background(self):
        from utils import transform_wordcloud
        badges = [("A", "data:image/png;base64,AAA", 1)]
        svg = transform_wordcloud(badges, preset="web", bg_color="#f8fafc")
        assert 'class="logo-plate"' not in svg

    def test_light_only_svg_gets_dark_plate(self):
        import base64
        from utils import transform_wordcloud
        white_svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path fill="#ffffff" d="M0 0h10v10z"/></svg>'
        uri = "data:image/svg+xml;base64," + base64.b64encode(white_svg).decode()
        badges = [("A", uri, 1)]
        dark = transform_wordcloud(badges, preset="web", theme="dark")
        light = transform_wordcloud(badges, preset="web", theme="light")
        assert 'fill="#475569"' in dark
        assert 'fill="#475569"' in light
