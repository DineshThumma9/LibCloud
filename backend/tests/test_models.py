from app.models import PKGInfo, ProjectLinks, merge_pkg_dicts
from app.processor import ValidationResult


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


class TestModelsAndAPIHelpers:
    def test_pkginfo_merge(self):
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
        res = ValidationResult(True, "valid_svg", "image/svg+xml")
        valid, reason = res
        assert valid is True
        assert reason == "valid_svg"
        assert res.mime_type == "image/svg+xml"

    def test_graph_github_api_lifecycle(self, monkeypatch):
        from app.services.scanning import GraphGithubAPI

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        api = GraphGithubAPI("test_user", token="ghp_test123")
        assert api.token_exists is True
        api_no_token = GraphGithubAPI("test_user")
        assert api_no_token.token_exists is False
