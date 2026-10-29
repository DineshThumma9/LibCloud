import contextlib
from collections import defaultdict
from unittest.mock import AsyncMock

import pytest

from app.models import PKGInfo
from app.services.scanning import GraphGithubAPI
from tests.helpers import make_api, manifest_nodes


class TestDependencyGraphLockfiles:
    @pytest.mark.anyio
    async def test_lockfile_manifests_are_skipped(self):
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


class TestManifestPackageEvents:
    @pytest.mark.anyio
    async def test_manifest_deltas_and_remaining_are_emitted_once(self):
        api, job_manager = make_api()

        async def fake_execute(*args, **kwargs):
            payload = manifest_nodes(
                ("package.json", ["react", "react", "next"]),
                ("requirements.txt", ["fastapi", "flask"]),
            )
            payload["repository"]["dockerfile"] = True
            return payload

        api.ghc.execute = fake_execute
        try:
            pkg_dic = await api.fetch_repo_deps("test-repo")
        finally:
            await api.aclose()

        packages = job_manager.emitted_packages()
        by_slug = defaultdict(int)
        for pkg in packages:
            by_slug[pkg["slug"]] += pkg["count"]

        # Resolver-compatible slugs (Next.js -> nextdotjs) and no duplicates.
        assert by_slug == {
            "react": 2,
            "nextdotjs": 1,
            "fastapi": 1,
            "flask": 1,
            "docker": 1,
        }
        assert {pkg["slug"] for pkg in packages}.isdisjoint({"React", "Next.js"})
        assert len(packages) == len(by_slug)

        event_types = [event_type for event_type, _ in job_manager.events]
        assert event_types[-1] == "repo.scan.done"
        assert event_types.count("package.found") == 3

        # The sum streamed to the frontend matches the backend aggregate.
        assert sum(by_slug.values()) == sum(p.count for p in pkg_dic.values())

    @pytest.mark.anyio
    async def test_emit_packages_uses_resolver_slug_and_display_name(self):
        api, job_manager = make_api()
        try:
            await api._emit_packages(
                "test-repo",
                {
                    "Next.js": PKGInfo(count=2, dep_origin="ts", raw_names={"next"}),
                    "Radix UI": PKGInfo(count=1, dep_origin="ts", raw_names={"@radix-ui/react"}),
                },
            )
        finally:
            await api.aclose()

        packages = job_manager.emitted_packages()
        assert packages == [
            {"slug": "nextdotjs", "name": "Next.js", "count": 2, "dep_origin": "ts"},
            {"slug": "radixui", "name": "Radix UI", "count": 1, "dep_origin": "ts"},
        ]


class TestCachedRepoPackageEvents:
    @pytest.mark.anyio
    async def test_cache_hit_emits_full_package_list_before_scan_done(self):
        cached = {
            "React": {"count": 3, "dep_origin": "ts", "raw_names": ["react"]},
            "FastAPI": {"count": 2, "dep_origin": "py", "raw_names": ["fastapi"]},
        }
        api, job_manager = make_api(cached=cached)
        try:
            pkg_dic = await api.fetch_repo_deps("test-repo")
        finally:
            await api.aclose()

        assert [event_type for event_type, _ in job_manager.events] == [
            "repo.scan.start",
            "package.found",
            "repo.scan.done",
        ]
        packages = {pkg["slug"]: pkg["count"] for pkg in job_manager.emitted_packages()}
        assert packages == {"react": 3, "fastapi": 2}
        assert sum(packages.values()) == sum(p.count for p in pkg_dic.values())
        assert job_manager.events[-1][1]["cache_hit"] is True


class TestCloneFallbackPackageEvents:
    @pytest.mark.anyio
    async def test_clone_fallback_emits_every_package_once(self, tmp_path, monkeypatch):
        api, job_manager = make_api()
        (tmp_path / "package.json").write_text(
            '{"dependencies": {"react": "^18.0.0", "next": "^14.0.0"}}',
            encoding="utf-8",
        )

        async def fake_execute(*args, **kwargs):
            return {"repository": {}}

        class FakeProcess:
            async def communicate(self):
                return b"", b""

        async def fake_subprocess(*args, **kwargs):
            return FakeProcess()

        monkeypatch.setattr(api.ghc, "execute", fake_execute)
        monkeypatch.setattr("app.services.scanning.asyncio.create_subprocess_exec", fake_subprocess)
        monkeypatch.setattr("app.services.scanning.tempfile.TemporaryDirectory", lambda: contextlib.nullcontext(tmp_path))

        try:
            pkg_dic = await api.fetch_repo_deps("test-repo")
        finally:
            await api.aclose()

        packages = job_manager.emitted_packages()
        by_slug = {pkg["slug"]: pkg["count"] for pkg in packages}
        assert by_slug == {"react": 1, "nextdotjs": 1}
        assert len(packages) == len(by_slug)
        assert [event_type for event_type, _ in job_manager.events][-2:] == [
            "package.found",
            "repo.scan.done",
        ]
        assert sum(by_slug.values()) == sum(p.count for p in pkg_dic.values())
