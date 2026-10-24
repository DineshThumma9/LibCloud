import pytest
import struct
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
            ("volley", "pom.xml", "Android", "java"),
            ("android-sdk", "pom.xml", "Android", "java"),
        ]

        for raw, fname, expected_norm, expected_lang in cases:
            norm, lang = parser.normalize_pkg(raw, fname)
            assert norm == expected_norm, f"Expected {raw} -> {expected_norm}, got {norm}"
            assert lang == expected_lang
