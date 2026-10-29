import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from app.constants import SLUG_MAP
from app.deps import get_db
from app.jobs import JobManager
from app.reporting.runs import RunContext
from app.services.icons import ImageResolver
from app.services.scanning import GraphGithubAPI

log = logging.getLogger(__name__)


def _build_summary(
    run: RunContext,
    started_monotonic: float,
    status: str,
    error: str,
    api: Optional[GraphGithubAPI],
    resolver: Optional[ImageResolver],
    package_count: int,
    resolved_count: int,
) -> dict:
    finished_at = datetime.now(timezone.utc)
    parser = api.parser if api else None
    failed_icons = resolver.failed_icons if resolver else []
    validation_failures = resolver.validation_failures if resolver else []
    unnormalized = parser.unnormalized_rows() if parser else []
    filtered = parser.can_records if parser else []

    summary = {
        "finished_at": finished_at,
        "status": status,
        "duration_ms": int((time.monotonic() - started_monotonic) * 1000),
        "repo_count": api.repo_count if api else 0,
        "package_count": package_count,
        "resolved_count": resolved_count,
        "failed_count": len(failed_icons),
        "unnormalized_count": len(unnormalized),
        "filtered_count": len(filtered),
        "validation_failure_count": len(validation_failures),
        "resolution_methods": dict(resolver.recovery_stats) if resolver else {},
    }
    if error:
        summary["error"] = error
    return summary


def _build_details(api: Optional[GraphGithubAPI], resolver: Optional[ImageResolver], badge_items):
    parser = api.parser if api else None
    resolved = []
    for norm_name, _icon, count in badge_items:
        resolved.append({
            "slug": SLUG_MAP.get(norm_name, norm_name).lower(),
            "norm_name": norm_name,
            "count": count,
            "method": resolver.resolved_methods.get(norm_name, "unknown") if resolver else "unknown",
            "source_url": resolver.resolved_urls.get(norm_name, "") if resolver else "",
        })

    return {
        "resolved": resolved,
        "failures": list(resolver.failed_icons) if resolver else [],
        "unnormalized": parser.unnormalized_rows() if parser else [],
        "filtered": list(parser.can_records) if parser else [],
        "validation": list(resolver.validation_failures) if resolver else [],
    }


async def run_pipeline(job_manager: JobManager, username: str, token: str = None):
    run = RunContext.create(username)
    db = get_db()
    started_monotonic = time.monotonic()
    status = "completed"
    error_message = ""
    api: Optional[GraphGithubAPI] = None
    resolver: Optional[ImageResolver] = None
    pkg_dic = {}
    badge_items = []

    try:
        await db.run_store.start_run(run)

        await job_manager.emit("job.accepted", {
            "username": username,
            "params": "",
            "job_taken": job_manager.job_id,
            "run_id": run.run_id,
        })

        async with GraphGithubAPI(username=username, token=token, job_manager=job_manager) as api:
            pkg_dic = await api.fetch_all_repos_deps()

            async with ImageResolver(github_token=token, job_manager=job_manager) as resolver:
                badge_items = await resolver.resolve(pkg_dic)
    except asyncio.CancelledError:
        status = "cancelled"
        raise
    except Exception as e:
        status = "failed"
        error_message = str(e)
    finally:
        summary = _build_summary(
            run=run,
            started_monotonic=started_monotonic,
            status=status,
            error=error_message,
            api=api,
            resolver=resolver,
            package_count=len(pkg_dic),
            resolved_count=len(badge_items),
        )
        details = _build_details(api, resolver, badge_items)
        try:
            await db.run_store.finish_run(run, summary, **details)
        except Exception:
            log.exception("Failed to persist run %s", run.run_id)

    if status == "failed":
        await job_manager.emit("error", {
            "phase": "pipeline",
            "message": error_message,
            "retryable": "true",
            "run_id": run.run_id,
        })
    else:
        await job_manager.emit("done", {
            "job_id": job_manager.job_id,
            "scene_url": "",
            "stats": "",
            "run_id": run.run_id,
        })
