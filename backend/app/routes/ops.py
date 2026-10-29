"""Read-only ops dashboard and JSON API, protected with HTTP Basic auth."""

from __future__ import annotations

import csv
import hmac
import io
import re
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings
from app.deps import get_db
from app.storage import DepsDB
from app.storage.runs import DETAIL_KINDS

basic_auth = HTTPBasic(auto_error=False)

_CSV_KINDS = {
    "resolved": "resolved",
    "failures": "failures",
    "failed": "failures",
    "unnormalized": "unnormalized",
    "filtered": "filtered",
    "validation": "validation",
}


def _configured() -> bool:
    return bool(settings.ops_user.strip() and settings.ops_password)


def _matches(supplied: str, expected: str) -> bool:
    return hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))


def require_ops_auth(
    credentials: Optional[HTTPBasicCredentials] = Depends(basic_auth),
) -> None:
    """Reject requests unless the configured ops credentials are supplied."""
    if not _configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ops dashboard is not configured. Set OPS_USER and OPS_PASSWORD.",
        )
    if (
        credentials is None
        or not _matches(credentials.username, settings.ops_user.strip())
        or not _matches(credentials.password, settings.ops_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ops credentials.",
            headers={"WWW-Authenticate": 'Basic realm="LibCloud ops", charset="UTF-8"'},
        )


router = APIRouter(dependencies=[Depends(require_ops_auth)])


def _clean_username(username: Optional[str]) -> Optional[str]:
    value = (username or "").strip().lower()
    return value or None


def _csv_safe(value: Any) -> str:
    """Prevent spreadsheet formula injection from package names."""
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


@router.get("/api/ops/summary")
async def ops_summary(db: DepsDB = Depends(get_db)):
    return await db.run_store.get_summary()


@router.get("/api/ops/runs")
async def ops_runs(
    username: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: DepsDB = Depends(get_db),
):
    runs = await db.run_store.list_runs(username=_clean_username(username), limit=limit)
    return {"runs": runs, "count": len(runs)}


@router.get("/api/ops/runs/{run_id}")
async def ops_run(run_id: str, db: DepsDB = Depends(get_db)):
    run = await db.run_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    details = await db.run_store.get_details(run_id)
    return {"run": run, "details": details}


@router.get("/api/ops/details/{kind}")
async def ops_details(
    kind: str,
    username: Optional[str] = None,
    limit: int = Query(2000, ge=1, le=5000),
    db: DepsDB = Depends(get_db),
):
    if kind not in DETAIL_KINDS:
        raise HTTPException(status_code=404, detail="Unknown detail kind")
    rows = await db.run_store.list_detail(
        kind,
        username=_clean_username(username),
        limit=limit,
    )
    return {"kind": kind, "rows": rows, "count": len(rows)}


@router.get("/api/ops/search")
async def ops_search(
    q: str = Query("", max_length=100),
    limit: int = Query(200, ge=1, le=200),
    db: DepsDB = Depends(get_db),
):
    query = q.strip()
    results = await db.run_store.search(query, limit=limit) if query else []
    return {"query": query, "results": results, "count": len(results)}


@router.get("/api/ops/runs/{run_id}/{kind}.csv")
async def ops_run_csv(run_id: str, kind: str, db: DepsDB = Depends(get_db)):
    detail_kind = _CSV_KINDS.get(kind)
    if not detail_kind:
        raise HTTPException(status_code=404, detail="Unknown export kind")
    run = await db.run_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    details = await db.run_store.get_details(run_id)
    rows = [
        {"run_id": run_id, "username": run.get("username", ""), **row}
        for row in details.get(detail_kind, [])
    ]
    fieldnames: list[str] = ["run_id", "username"]
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows([
        {key: _csv_safe(value) for key, value in row.items()}
        for row in rows
    ])

    filename = re.sub(r"[^A-Za-z0-9._-]+", "-", f"{run_id}-{detail_kind}") + ".csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
