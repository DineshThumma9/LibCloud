import contextlib
import sys
from collections import defaultdict
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# Ensure src is in sys.path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


class RecordingJobManager:
    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    async def emit(self, event_type, data):
        self.events.append((event_type, data))

    def package_events(self):
        return [data for event_type, data in self.events if event_type == "package.found"]

    def emitted_packages(self):
        packages = []
        for event in self.package_events():
            packages.extend(event["packages"])
        return packages


class FakeDepDB:
    def __init__(self, cached=None):
        self.cached = cached

    async def get_repo_deps(self, **kwargs):
        return self.cached

    async def save_repo_deps(self, **kwargs):
        return None


def make_api(cached=None):
    from api import GraphGithubAPI

    job_manager = RecordingJobManager()
    api = GraphGithubAPI("test_user", job_manager=job_manager)
    api.dep_db = FakeDepDB(cached)
    return api, job_manager


def manifest_nodes(*manifests):
    return {
        "repository": {
            "dependencyGraphManifests": {
                "nodes": [
                    {
                        "filename": filename,
                        "dependencies": {
                            "nodes": [{"packageName": name} for name in names]
                        },
                    }
                    for filename, names in manifests
                ]
            }
        }
    }


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
        from models import PKGInfo

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
        monkeypatch.setattr("api.asyncio.create_subprocess_exec", fake_subprocess)
        monkeypatch.setattr("api.tempfile.TemporaryDirectory", lambda: contextlib.nullcontext(tmp_path))

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
