"""MongoDB records for scan runs and their failure/detail rows."""

from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.reporting.runs import RunContext
from app.storage.base import BaseStore

log = logging.getLogger(__name__)

# Public detail kinds exposed by the dashboard and ops API.
DETAIL_KINDS = ("resolved", "failures", "unnormalized", "filtered", "validation")

_SEARCH_FIELDS = {
    "resolved": ("norm_name", "slug"),
    "failures": ("norm_name", "raw_name", "slug_tried"),
    "unnormalized": ("cleaned_name", "raw_name"),
    "filtered": ("raw_name", "cleaned_name", "norm_name"),
    "validation": ("url", "reason"),
}

_MAX_LIST_LIMIT = 200
_MAX_DETAIL_LIMIT = 5000

_SECRET_PATTERN = re.compile(
    r"(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,})"
)
_SECRET_QUERY_PATTERN = re.compile(r"(?i)\b(token|access_token|password|secret)=([^&\s]+)")


def _redact(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    value = _SECRET_PATTERN.sub("[redacted]", value)
    return _SECRET_QUERY_PATTERN.sub(r"\1=[redacted]", value)


def _as_timestamp(value: Any) -> float:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _normalize_timestamps(doc: dict[str, Any]) -> dict[str, Any]:
    """Mongo returns naive UTC datetimes; make them explicit for API clients."""
    for field in ("started_at", "finished_at"):
        value = doc.get(field)
        if isinstance(value, datetime) and value.tzinfo is None:
            doc[field] = value.replace(tzinfo=timezone.utc)
    return doc


def _public_run(doc: dict[str, Any]) -> dict[str, Any]:
    """Strip request params and anything token-like before exposing a run."""
    _normalize_timestamps(doc)
    doc.pop("params", None)
    for key in list(doc):
        lowered = key.lower()
        if any(part in lowered for part in ("token", "password", "secret", "authorization")):
            doc.pop(key, None)
    if "error" in doc:
        doc["error"] = _redact(doc["error"])
    return doc


def _public_row(row: dict[str, Any]) -> dict[str, Any]:
    public = {key: _redact(value) for key, value in row.items()}
    # Manifest paths can contain owner/repo names; keep only the filename.
    origin = public.get("origin_path")
    if isinstance(origin, str) and origin:
        public["origin_path"] = origin.replace("\\", "/").rsplit("/", 1)[-1]
    return public


class RunStore(BaseStore):
    """Persist one run summary plus its detail rows for the ops dashboard."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db)
        self.runs = db["runs"]
        self.resolved = db["run_resolved"]
        self.failures = db["run_failures"]
        self.unnormalized = db["run_unnormalized"]
        self.filtered = db["run_filtered"]
        self.validation = db["run_validation"]
        self._indexes_ready = False
        self._mem_runs: dict[str, dict] = {}
        self._mem_details: dict[str, dict[str, list[dict]]] = {}

    async def ensure_indexes(self):
        if self._indexes_ready or not self._db_available:
            return
        try:
            await self.runs.create_index("run_id", unique=True)
            await self.runs.create_index([("username", 1), ("started_at", -1)])
            await self.failures.create_index("run_id")
            await self.failures.create_index([("username", 1), ("norm_name", 1)])
            await self.unnormalized.create_index("run_id")
            await self.unnormalized.create_index([("username", 1), ("cleaned_name", 1)])
            await self.resolved.create_index("run_id")
            await self.filtered.create_index("run_id")
            await self.validation.create_index("run_id")
        except Exception as e:
            self._warn_db(e)
        finally:
            self._indexes_ready = True

    async def start_run(self, run: RunContext, params: Optional[dict] = None):
        doc = {
            "run_id": run.run_id,
            "username": run.username,
            "started_at": run.started_at,
            "finished_at": None,
            "status": "running",
            "params": params or {},
        }
        self._mem_runs[run.run_id] = doc
        await self.ensure_indexes()
        await self._upsert_run(doc)

    async def finish_run(
        self,
        run: RunContext,
        summary: dict[str, Any],
        *,
        resolved: Iterable[dict] = (),
        failures: Iterable[dict] = (),
        unnormalized: Iterable[dict] = (),
        filtered: Iterable[dict] = (),
        validation: Iterable[dict] = (),
    ):
        doc = {
            **summary,
            "run_id": run.run_id,
            "username": run.username,
            "started_at": run.started_at,
        }
        self._mem_runs[run.run_id] = doc
        await self._upsert_run(doc)

        details = {
            "resolved": list(resolved),
            "failures": list(failures),
            "unnormalized": list(unnormalized),
            "filtered": list(filtered),
            "validation": list(validation),
        }
        self._mem_details[run.run_id] = details
        for kind, rows in details.items():
            await self._insert_details(kind, run, rows)

    async def get_summary(self) -> dict[str, Any]:
        """Aggregate counts for the overview page, Mongo-first with memory fallback."""
        runs = await self._load_runs()
        runs.sort(key=lambda doc: _as_timestamp(doc.get("started_at")), reverse=True)

        statuses = Counter((doc.get("status") or "unknown") for doc in runs)
        totals = {field: sum(int(doc.get(field) or 0) for doc in runs) for field in (
            "repo_count",
            "package_count",
            "resolved_count",
            "failed_count",
            "unnormalized_count",
            "filtered_count",
            "validation_failure_count",
        )}

        users: dict[str, dict[str, Any]] = {}
        for doc in runs:
            username = doc.get("username") or "unknown"
            entry = users.setdefault(username, {"username": username, "runs": 0, "last_started_at": None})
            entry["runs"] += 1
            started = doc.get("started_at")
            if entry["last_started_at"] is None or _as_timestamp(started) > _as_timestamp(entry["last_started_at"]):
                entry["last_started_at"] = started

        attempts = totals["resolved_count"] + totals["failed_count"]
        return {
            "generated_at": datetime.now(timezone.utc),
            "runs": {
                "total": len(runs),
                "completed": statuses.get("completed", 0),
                "failed": statuses.get("failed", 0),
                "cancelled": statuses.get("cancelled", 0),
                "running": statuses.get("running", 0),
            },
            "totals": totals,
            "rates": {
                "resolved": self._rate(totals["resolved_count"], attempts),
                "failed": self._rate(totals["failed_count"], attempts),
            },
            "users": sorted(users.values(), key=lambda item: _as_timestamp(item["last_started_at"]), reverse=True),
            "recent": runs[:15],
        }

    async def list_runs(self, username: Optional[str] = None, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), _MAX_LIST_LIMIT))
        username = (username or "").strip().lower() or None

        if self._db_available:
            query = {"username": username} if username else {}
            try:
                cursor = self.runs.find(query, {"_id": 0}).sort("started_at", -1).limit(limit)
                return [_public_run(doc) for doc in await cursor.to_list(None)]
            except Exception as e:
                self._warn_db(e)

        runs = [
            dict(doc)
            for doc in self._mem_runs.values()
            if not username or doc.get("username") == username
        ]
        runs.sort(key=lambda doc: _as_timestamp(doc.get("started_at")), reverse=True)
        return [_public_run(doc) for doc in runs[:limit]]

    async def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        if self._db_available:
            try:
                doc = await self.runs.find_one({"run_id": run_id}, {"_id": 0})
                if doc:
                    return _public_run(doc)
            except Exception as e:
                self._warn_db(e)

        doc = self._mem_runs.get(run_id)
        return _public_run(dict(doc)) if doc else None

    async def get_details(self, run_id: str) -> dict[str, list[dict]]:
        memory = self._memory_details(run_id)

        if not self._db_available:
            return memory

        try:
            details: dict[str, list[dict]] = {}
            for kind in DETAIL_KINDS:
                collection = getattr(self, kind)
                cursor = collection.find({"run_id": run_id}, {"_id": 0})
                details[kind] = [_public_row(row) for row in await cursor.to_list(None)]
        except Exception as e:
            self._warn_db(e)
            return memory

        # Supplement anything missing from Mongo with rows still held in memory.
        for kind, rows in memory.items():
            if not details.get(kind) and rows:
                details[kind] = rows
        return details

    async def list_detail(
        self,
        kind: str,
        *,
        username: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 2000,
    ) -> list[dict[str, Any]]:
        if kind not in DETAIL_KINDS:
            raise ValueError(f"Unknown detail kind: {kind}")
        limit = max(1, min(int(limit), _MAX_DETAIL_LIMIT))
        username = (username or "").strip().lower() or None

        if self._db_available:
            query: dict[str, Any] = {}
            if username:
                query["username"] = username
            if run_id:
                query["run_id"] = run_id
            try:
                collection = getattr(self, kind)
                cursor = collection.find(query, {"_id": 0}).sort("count", -1).limit(limit)
                return [_public_row(row) for row in await cursor.to_list(None)]
            except Exception as e:
                self._warn_db(e)

        rows = self._memory_detail_rows(kind)
        if username:
            rows = [row for row in rows if row.get("username") == username]
        if run_id:
            rows = [row for row in rows if row.get("run_id") == run_id]
        rows.sort(key=lambda row: int(row.get("count") or 0), reverse=True)
        return [_public_row(row) for row in rows[:limit]]

    async def search(self, query: str, limit: int = 100) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query or len(query) > 100:
            return []
        limit = max(1, min(int(limit), _MAX_LIST_LIMIT))
        pattern = re.escape(query)

        if self._db_available:
            try:
                results: list[dict[str, Any]] = []
                for kind in DETAIL_KINDS:
                    fields = _SEARCH_FIELDS[kind]
                    collection = getattr(self, kind)
                    cursor = collection.find(
                        {"$or": [{field: {"$regex": pattern, "$options": "i"}} for field in fields]},
                        {"_id": 0},
                    ).sort("count", -1).limit(limit)
                    results.extend(_public_row({**row, "kind": kind}) for row in await cursor.to_list(None))
                results.sort(key=lambda row: int(row.get("count") or 0), reverse=True)
                return results[:limit]
            except Exception as e:
                self._warn_db(e)

        needle = query.casefold()
        results = []
        for kind in DETAIL_KINDS:
            fields = _SEARCH_FIELDS[kind]
            for row in self._memory_detail_rows(kind):
                if any(needle in str(row.get(field, "")).casefold() for field in fields):
                    results.append(_public_row({**row, "kind": kind}))
        results.sort(key=lambda row: int(row.get("count") or 0), reverse=True)
        return results[:limit]

    async def _load_runs(self) -> list[dict[str, Any]]:
        if self._db_available:
            try:
                cursor = self.runs.find({}, {"_id": 0})
                return [_public_run(doc) for doc in await cursor.to_list(None)]
            except Exception as e:
                self._warn_db(e)
        return [_public_run(dict(doc)) for doc in self._mem_runs.values()]

    def _memory_details(self, run_id: str) -> dict[str, list[dict]]:
        stored = self._mem_details.get(run_id) or {}
        return {
            kind: [_public_row(dict(row)) for row in stored.get(kind, [])]
            for kind in DETAIL_KINDS
        }

    def _memory_detail_rows(self, kind: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for run_id, stored in self._mem_details.items():
            run = self._mem_runs.get(run_id, {})
            for row in stored.get(kind, []):
                rows.append({**row, "run_id": run_id, "username": run.get("username", "")})
        return rows

    @staticmethod
    def _rate(part: int, total: int) -> float:
        return round(part / total, 4) if total else 0.0

    async def _upsert_run(self, doc: dict):
        if not self._db_available:
            return
        try:
            await self.runs.update_one(
                {"run_id": doc["run_id"]},
                {"$set": doc},
                upsert=True,
            )
        except Exception as e:
            self._warn_db(e)

    async def _insert_details(self, kind: str, run: RunContext, rows: list[dict]):
        if not rows or not self._db_available:
            return
        collection = getattr(self, kind)
        docs = [
            {**row, "run_id": run.run_id, "username": run.username}
            for row in rows
        ]
        try:
            await collection.insert_many(docs)
        except Exception as e:
            self._warn_db(e)
