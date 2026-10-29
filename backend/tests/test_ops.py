import re
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.deps import get_db
from app.main import create_app
from app.reporting.runs import RunContext
from app.routes.ops import _csv_safe
from app.storage.runs import RunStore


class FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, key, direction=-1):
        self.docs.sort(
            key=lambda doc: (doc.get(key) is not None, doc.get(key) or 0),
            reverse=direction == -1,
        )
        return self

    def limit(self, count):
        self.docs = self.docs[:count]
        return self

    async def to_list(self, length):
        return self.docs[:length] if length else self.docs


def _matches(doc, query):
    for key, expected in query.items():
        if key == "$or":
            if not any(_matches(doc, clause) for clause in expected):
                return False
            continue
        if isinstance(expected, dict) and "$regex" in expected:
            flags = re.IGNORECASE if "i" in expected.get("$options", "") else 0
            if not re.search(expected["$regex"], str(doc.get(key, "")), flags):
                return False
            continue
        if doc.get(key) != expected:
            return False
    return True


class FakeCollection:
    def __init__(self):
        self.docs = []
        self.indexes = []

    async def create_index(self, *args, **kwargs):
        self.indexes.append((args, kwargs))

    async def update_one(self, query, update, upsert=False):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                doc.update(update.get("$set", {}))
                return
        if upsert:
            self.docs.append({**query, **update.get("$set", {})})

    async def insert_many(self, docs):
        self.docs.extend(docs)

    async def find_one(self, query, projection=None):
        for doc in self.docs:
            if _matches(doc, query):
                result = dict(doc)
                if projection:
                    result.pop("_id", None)
                return result
        return None

    def find(self, query, projection=None):
        docs = []
        for doc in self.docs:
            if _matches(doc, query):
                result = dict(doc)
                if projection:
                    result.pop("_id", None)
                docs.append(result)
        return FakeCursor(docs)


class FakeDB:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        return self.collections.setdefault(name, FakeCollection())


def make_run(username="octocat", run_id="run-1", hour=6):
    return RunContext(
        username=username,
        run_id=run_id,
        started_at=datetime(2026, 10, 29, hour, 0, tzinfo=timezone.utc),
    )


async def seed_store():
    store = RunStore(FakeDB())
    first = make_run(run_id="run-1", hour=6)
    second = make_run(run_id="run-2", hour=7)

    await store.start_run(first)
    await store.finish_run(
        first,
        {
            "finished_at": datetime(2026, 10, 29, 6, 1, tzinfo=timezone.utc),
            "status": "completed",
            "duration_ms": 60000,
            "repo_count": 4,
            "package_count": 10,
            "resolved_count": 8,
            "failed_count": 2,
            "unnormalized_count": 1,
            "filtered_count": 3,
            "validation_failure_count": 1,
            "resolution_methods": {"cdn_catalog": 8},
        },
        resolved=[
            {
                "slug": "react",
                "norm_name": "React",
                "count": 5,
                "method": "cdn_catalog",
                "source_url": "https://cdn.simpleicons.org/react",
            }
        ],
        failures=[
            {
                "norm_name": "Nope",
                "raw_name": "nope-py",
                "dep_origin": "python",
                "count": 2,
                "slug_tried": "nope",
                "reason": "no_icon_found",
            }
        ],
        unnormalized=[
            {
                "cleaned_name": "unknown-pkg",
                "raw_name": "unknown-pkg",
                "count": 4,
                "language": "python",
                "dep_origin": "pyproject.toml",
                "origin_path": "acme/private-repo/pyproject.toml",
            }
        ],
        filtered=[
            {
                "raw_name": "typing-extensions",
                "cleaned_name": "typing-extensions",
                "language": "python",
                "dep_origin": "requirements.txt",
                "reason": "noise_blocklist",
                "origin_path": "acme/private-repo/requirements.txt",
            }
        ],
        validation=[
            {
                "url": "https://example.test/bad.svg",
                "reason": "bad_content_type",
                "size_bytes": 42,
            }
        ],
    )

    await store.start_run(second)
    await store.finish_run(
        second,
        {
            "finished_at": datetime(2026, 10, 29, 7, 1, tzinfo=timezone.utc),
            "status": "failed",
            "duration_ms": 5000,
            "repo_count": 1,
            "package_count": 0,
            "resolved_count": 0,
            "failed_count": 0,
            "unnormalized_count": 0,
            "filtered_count": 0,
            "validation_failure_count": 0,
            "resolution_methods": {},
            "error": "rate limited for ghp_" + "a" * 36,
        },
    )
    return store


@pytest.fixture
def client(monkeypatch):
    store_holder = {}

    async def seed():
        if "store" not in store_holder:
            store_holder["store"] = await seed_store()
        return store_holder["store"]

    import anyio

    store = anyio.run(seed)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: SimpleNamespace(run_store=store)
    monkeypatch.setattr(settings, "ops_user", "ops")
    monkeypatch.setattr(settings, "ops_password", "secret")
    return TestClient(app)


class TestOpsAuth:
    def test_unconfigured_returns_503_and_noindex(self, monkeypatch):
        app = create_app()
        app.dependency_overrides[get_db] = lambda: SimpleNamespace()
        monkeypatch.setattr(settings, "ops_user", "")
        monkeypatch.setattr(settings, "ops_password", "")
        client = TestClient(app)

        response = client.get("/api/ops/summary")
        assert response.status_code == 503
        assert response.headers["x-robots-tag"] == "noindex, nofollow"

    def test_bad_credentials_return_401(self, client):
        response = client.get("/api/ops/summary", auth=("ops", "wrong"))
        assert response.status_code == 401
        assert response.headers["www-authenticate"].startswith("Basic")
        assert response.headers["x-robots-tag"] == "noindex, nofollow"

    def test_missing_credentials_return_401(self, client):
        assert client.get("/api/ops/summary").status_code == 401

    def test_valid_credentials_open_api(self, client):
        response = client.get("/api/ops/summary", auth=("ops", "secret"))
        assert response.status_code == 200
        assert response.headers["x-robots-tag"] == "noindex, nofollow"
        assert response.json()["runs"]["total"] == 2


class TestOpsApi:
    def test_summary_payload(self, client):
        response = client.get("/api/ops/summary", auth=("ops", "secret"))
        assert response.status_code == 200
        payload = response.json()
        assert payload["runs"] == {
            "total": 2,
            "completed": 1,
            "failed": 1,
            "cancelled": 0,
            "running": 0,
        }
        assert payload["totals"]["repo_count"] == 5
        assert payload["totals"]["resolved_count"] == 8
        assert payload["rates"]["resolved"] == 0.8
        assert payload["users"][0]["username"] == "octocat"
        assert payload["recent"][0]["run_id"] == "run-2"
        assert payload["recent"][0]["started_at"].endswith("+00:00")

    def test_run_list_filters_and_limits(self, client):
        response = client.get(
            "/api/ops/runs?username=OctoCat&limit=1",
            auth=("ops", "secret"),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        assert payload["runs"][0]["run_id"] == "run-2"

        none = client.get(
            "/api/ops/runs?username=someone-else",
            auth=("ops", "secret"),
        )
        assert none.json() == {"runs": [], "count": 0}

    def test_run_detail_payload(self, client):
        response = client.get("/api/ops/runs/run-1", auth=("ops", "secret"))
        assert response.status_code == 200
        payload = response.json()
        assert payload["run"]["username"] == "octocat"
        assert payload["run"]["status"] == "completed"
        assert "params" not in payload["run"]
        assert payload["details"]["resolved"][0]["slug"] == "react"
        assert payload["details"]["failures"][0]["norm_name"] == "Nope"
        assert payload["details"]["unnormalized"][0]["cleaned_name"] == "unknown-pkg"
        assert payload["details"]["unnormalized"][0]["origin_path"] == "pyproject.toml"
        assert payload["details"]["filtered"][0]["reason"] == "noise_blocklist"
        assert payload["details"]["filtered"][0]["origin_path"] == "requirements.txt"
        assert "acme/private-repo" not in response.text
        assert payload["details"]["validation"][0]["size_bytes"] == 42

        missing = client.get("/api/ops/runs/missing", auth=("ops", "secret"))
        assert missing.status_code == 404

    def test_run_error_redacts_tokens(self, client):
        response = client.get("/api/ops/runs/run-2", auth=("ops", "secret"))
        assert response.status_code == 200
        error = response.json()["run"]["error"]
        assert "ghp_" not in error
        assert "[redacted]" in error

    def test_ops_api_noindex(self, client):
        response = client.get("/api/ops/runs", auth=("ops", "secret"))
        assert response.headers["x-robots-tag"] == "noindex, nofollow"
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


class TestOpsCollections:
    def test_details_endpoint(self, client):
        response = client.get(
            "/api/ops/details/failures?username=OctoCat",
            auth=("ops", "secret"),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["kind"] == "failures"
        assert payload["count"] == 1
        assert payload["rows"][0]["norm_name"] == "Nope"
        assert payload["rows"][0]["run_id"] == "run-1"
        assert payload["rows"][0]["username"] == "octocat"

        unknown = client.get("/api/ops/details/secrets", auth=("ops", "secret"))
        assert unknown.status_code == 404

    def test_search_endpoint(self, client):
        response = client.get("/api/ops/search?q=react", auth=("ops", "secret"))
        assert response.status_code == 200
        payload = response.json()
        assert payload["query"] == "react"
        assert payload["count"] == 1
        assert payload["results"][0]["kind"] == "resolved"
        assert payload["results"][0]["norm_name"] == "React"

        empty = client.get("/api/ops/search", auth=("ops", "secret"))
        assert empty.json() == {"query": "", "results": [], "count": 0}

    def test_search_is_parameterized(self, client):
        response = client.get(
            "/api/ops/search",
            params={"q": ".*"},
            auth=("ops", "secret"),
        )
        assert response.status_code == 200
        assert response.json()["count"] == 0

    def test_csv_values_are_formula_safe(self):
        assert _csv_safe("=HYPERLINK()") == "'=HYPERLINK()"
        assert _csv_safe("+cmd") == "'+cmd"
        assert _csv_safe("react") == "react"
        assert _csv_safe(None) == ""

    def test_run_csv_export(self, client):
        response = client.get(
            "/api/ops/runs/run-1/failures.csv",
            auth=("ops", "secret"),
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=" in response.headers["content-disposition"]
        assert response.text.splitlines()[0].startswith("run_id,username")
        assert "Nope" in response.text

        bad_kind = client.get(
            "/api/ops/runs/run-1/nope.csv",
            auth=("ops", "secret"),
        )
        assert bad_kind.status_code == 404

        missing_run = client.get(
            "/api/ops/runs/missing/failures.csv",
            auth=("ops", "secret"),
        )
        assert missing_run.status_code == 404


class TestRunStoreReads:
    @pytest.mark.anyio
    async def test_summary_and_reads_come_from_mongo(self):
        store = await seed_store()

        summary = await store.get_summary()
        assert summary["runs"]["total"] == 2
        assert summary["totals"] == {
            "repo_count": 5,
            "package_count": 10,
            "resolved_count": 8,
            "failed_count": 2,
            "unnormalized_count": 1,
            "filtered_count": 3,
            "validation_failure_count": 1,
        }
        assert summary["recent"][0]["run_id"] == "run-2"
        assert summary["recent"][0]["started_at"].tzinfo is not None

        runs = await store.list_runs(limit=1)
        assert [run["run_id"] for run in runs] == ["run-2"]

        details = await store.get_details("run-1")
        assert details["resolved"][0]["norm_name"] == "React"
        assert details["validation"][0]["url"] == "https://example.test/bad.svg"

        failures = await store.list_detail("failures")
        assert failures[0]["run_id"] == "run-1"
        assert failures[0]["username"] == "octocat"

        results = await store.search("react")
        assert [row["kind"] for row in results] == ["resolved"]
        assert results[0]["slug"] == "react"

    @pytest.mark.anyio
    async def test_reads_fall_back_to_memory(self):
        store = RunStore(FakeDB())
        store._db_available = False
        run = make_run(run_id="mem-1")

        await store.start_run(run)
        await store.finish_run(
            run,
            {
                "finished_at": None,
                "status": "completed",
                "duration_ms": 10,
                "repo_count": 1,
                "package_count": 2,
                "resolved_count": 1,
                "failed_count": 1,
                "unnormalized_count": 0,
                "filtered_count": 0,
                "validation_failure_count": 0,
                "resolution_methods": {"db_cache": 1},
            },
            resolved=[{"slug": "react", "norm_name": "React", "count": 1}],
            failures=[{"norm_name": "Nope", "raw_name": "nope", "count": 1}],
        )

        summary = await store.get_summary()
        assert summary["runs"]["total"] == 1
        assert summary["totals"]["resolved_count"] == 1

        assert (await store.list_runs())[0]["run_id"] == "mem-1"
        assert (await store.get_run("mem-1"))["status"] == "completed"

        details = await store.get_details("mem-1")
        assert details["resolved"][0]["slug"] == "react"
        assert details["failures"][0]["raw_name"] == "nope"

        failures = await store.list_detail("failures")
        assert failures[0]["run_id"] == "mem-1"
        assert failures[0]["username"] == "octocat"

        assert (await store.search("nope"))[0]["kind"] == "failures"
        assert await store.get_run("missing") is None
