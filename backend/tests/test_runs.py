import time
from collections import Counter
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.reporting.runs import RunContext, sanitize_username
from app.services.pipeline import _build_details, _build_summary, run_pipeline
from app.storage.runs import RunStore
from tests.helpers import RecordingJobManager


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


class FakeDB:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        return self.collections.setdefault(name, FakeCollection())


class TestRunContext:
    def test_username_is_path_and_log_safe(self):
        assert sanitize_username(" Octo Cat ") == "octo-cat"
        assert sanitize_username("../etc") == "etc"
        assert sanitize_username("") == "unknown"

    def test_run_ids_are_unique(self):
        first = RunContext.create("OctoCat")
        second = RunContext.create("OctoCat")

        assert first.username == "octocat"
        assert first.run_id != second.run_id
        assert first.started_at.tzinfo is not None


class TestRunStore:
    @pytest.mark.anyio
    async def test_run_summary_and_details_are_recorded(self):
        db = FakeDB()
        store = RunStore(db)
        run = RunContext.create("OctoCat")

        await store.start_run(run)
        await store.finish_run(
            run,
            {
                "finished_at": run.started_at,
                "status": "completed",
                "duration_ms": 123,
                "repo_count": 2,
                "package_count": 10,
                "resolved_count": 8,
                "failed_count": 2,
                "unnormalized_count": 1,
                "filtered_count": 1,
                "validation_failure_count": 0,
                "resolution_methods": {"cdn_catalog": 8},
            },
            resolved=[{"norm_name": "React", "count": 3}],
            failures=[{"norm_name": "Nope", "count": 1}],
            unnormalized=[{"cleaned_name": "x"}],
            filtered=[{"raw_name": "noise"}],
            validation=[],
        )

        run_docs = db["runs"].docs
        assert len(run_docs) == 1
        assert run_docs[0]["run_id"] == run.run_id
        assert run_docs[0]["username"] == "octocat"
        assert run_docs[0]["status"] == "completed"
        assert run_docs[0]["resolution_methods"] == {"cdn_catalog": 8}

        assert db["run_resolved"].docs[0]["run_id"] == run.run_id
        assert db["run_failures"].docs[0]["username"] == "octocat"
        assert db["run_unnormalized"].docs[0]["cleaned_name"] == "x"
        assert db["run_filtered"].docs[0]["raw_name"] == "noise"
        assert db["run_validation"].docs == []

        # Index setup runs once, not per detail collection.
        assert len(db["runs"].indexes) == 2


class TestRunSummary:
    def test_summary_and_details_include_audit_data(self):
        run = RunContext.create("OctoCat")
        api = SimpleNamespace(
            repo_count=4,
            parser=SimpleNamespace(
                unnormalized_rows=lambda: [{"cleaned_name": "unknown", "count": 2}],
                can_records=[{"raw_name": "noise", "reason": "noise_blocklist"}],
            ),
        )
        resolver = SimpleNamespace(
            failed_icons=[{"norm_name": "Nope", "reason": "no_icon_found"}],
            validation_failures=[{"url": "https://x.test/a.svg", "reason": "bad"}],
            recovery_stats=Counter({"cdn_catalog": 2}),
            resolved_methods={"React": "cdn_catalog"},
            resolved_urls={"React": "https://cdn.simpleicons.org/react"},
        )

        summary = _build_summary(
            run=run,
            started_monotonic=time.monotonic(),
            status="completed",
            error="",
            api=api,
            resolver=resolver,
            package_count=10,
            resolved_count=1,
        )
        details = _build_details(api, resolver, [("React", "data:image/svg+xml;base64,AAA", 3)])

        assert summary["repo_count"] == 4
        assert summary["package_count"] == 10
        assert summary["resolved_count"] == 1
        assert summary["failed_count"] == 1
        assert summary["unnormalized_count"] == 1
        assert summary["filtered_count"] == 1
        assert summary["validation_failure_count"] == 1
        assert summary["resolution_methods"] == {"cdn_catalog": 2}

        assert details["resolved"] == [{
            "slug": "react",
            "norm_name": "React",
            "count": 3,
            "method": "cdn_catalog",
            "source_url": "https://cdn.simpleicons.org/react",
        }]
        assert details["failures"] == resolver.failed_icons
        assert details["unnormalized"] == [{"cleaned_name": "unknown", "count": 2}]
        assert details["filtered"] == api.parser.can_records
        assert details["validation"] == resolver.validation_failures


class TestPipelineRecording:
    @pytest.mark.anyio
    async def test_pipeline_records_run_and_adds_run_id_to_events(self, monkeypatch):
        store = SimpleNamespace(start_run=AsyncMock(), finish_run=AsyncMock())
        monkeypatch.setattr(
            "app.services.pipeline.get_db",
            lambda: SimpleNamespace(run_store=store),
        )

        class FakeAPI:
            def __init__(self, *args, **kwargs):
                self.repo_count = 1
                self.parser = SimpleNamespace(
                    unnormalized_rows=lambda: [],
                    can_records=[],
                )

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def fetch_all_repos_deps(self):
                return {}

        class FakeResolver:
            def __init__(self, *args, **kwargs):
                self.failed_icons = []
                self.validation_failures = []
                self.recovery_stats = Counter()
                self.resolved_methods = {"React": "cdn_catalog"}
                self.resolved_urls = {"React": "https://cdn.simpleicons.org/react"}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def resolve(self, pkg_dic):
                return [("React", "data:image/svg+xml;base64,AAA", 1)]

        monkeypatch.setattr("app.services.pipeline.GraphGithubAPI", FakeAPI)
        monkeypatch.setattr("app.services.pipeline.ImageResolver", FakeResolver)

        job_manager = RecordingJobManager()
        await run_pipeline(job_manager, "OctoCat", token=None)

        event_types = [event_type for event_type, _ in job_manager.events]
        assert event_types == ["job.accepted", "done"]
        run_id = job_manager.events[0][1]["run_id"]
        assert run_id
        assert job_manager.events[1][1]["run_id"] == run_id

        store.start_run.assert_awaited_once()
        store.finish_run.assert_awaited_once()
        summary = store.finish_run.await_args.args[1]
        assert summary["status"] == "completed"
        assert summary["resolved_count"] == 1
        assert summary["repo_count"] == 1
        assert store.finish_run.await_args.kwargs["resolved"] == [{
            "slug": "react",
            "norm_name": "React",
            "count": 1,
            "method": "cdn_catalog",
            "source_url": "https://cdn.simpleicons.org/react",
        }]
