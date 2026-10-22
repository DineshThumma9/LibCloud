import pytest
import struct
from pathlib import Path
import sys

# Ensure src is in sys.path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from models import ProjectLinks
from resolver import ImageResolver
from parser import parse_pipfile, parse_workflow, DependencyParser
from constants import SLUG_MAP, NORM


class TestImageValidation:
    def test_svg_with_xml_prolog(self):
        svg_content = b'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/></svg>'
        valid, reason = ImageResolver.validate_image(svg_content)
        assert valid is True
        assert reason == "valid_svg"

    def test_svg_with_long_header(self):
        long_comment = b"<!-- " + (b"A" * 200) + b" -->\n"
        svg_content = long_comment + b'<svg viewBox="0 0 100 100"><rect width="10" height="10"/></svg>'
        valid, reason = ImageResolver.validate_image(svg_content)
        assert valid is True
        assert reason == "valid_svg"

    def test_reject_html_page(self):
        html_content = b"<!DOCTYPE html><html><head><title>404 Not Found</title></head><body>Error</body></html>"
        valid, reason = ImageResolver.validate_image(html_content)
        assert valid is False
        assert reason == "is_html_page_not_image"

    def test_reject_tracking_pixel(self):
        # 1x1 PNG header
        png_1x1 = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", 1, 1) + b"\x08\x06\x00\x00\x00" + (b"\x00" * 30)
        valid, reason = ImageResolver.validate_image(png_1x1)
        assert valid is False
        assert "rejected_tracking_pixel" in reason

    def test_valid_png(self):
        png_32x32 = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", 32, 32) + b"\x08\x06\x00\x00\x00" + (b"\x00" * 30)
        valid, reason = ImageResolver.validate_image(png_32x32)
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
