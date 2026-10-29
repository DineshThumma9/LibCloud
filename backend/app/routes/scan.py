import asyncio
from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from app.events import stream_events
from app.jobs import JobManager
from app.services.pipeline import run_pipeline

router = APIRouter()


@router.api_route("/framecloud/stream", methods=["GET", "POST"])
@router.api_route("/framecloud", methods=["GET", "POST"])
@router.api_route("/libcloud", methods=["GET", "POST"])
async def libcloud(
    username: str,
    request: Request,
    token: Optional[str] = None,
    preset: str = Query("web", description="Preset mode: 'web' (max space, 1400x900) or 'readme' (standard GitHub card, 920x540)"),
    width: Optional[int] = Query(None, description="Custom canvas width in pixels"),
    height: Optional[int] = Query(None, description="Custom canvas height in pixels"),
    min_size: Optional[int] = Query(None, description="Minimum logo size in pixels"),
    max_size: Optional[int] = Query(None, description="Maximum logo size in pixels"),
    padding: Optional[int] = Query(None, description="Padding between logos in pixels"),
    max_logos: Optional[int] = Query(None, description="Max logos to display (default: all)"),
    bg_color: Optional[str] = Query(None, description="Background hex color (defaults based on theme)"),
    theme: Optional[str] = Query(None, description="Theme: 'dark' (light logo plates) or 'light' (original logos)"),
):
    auth = request.headers.get("authorization", "")
    if not token and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()

    job_manager = JobManager()
    job_task = asyncio.create_task(run_pipeline(job_manager, username, token))

    return StreamingResponse(
        stream_events(job_manager.queue, job_task, request),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
        media_type="text/event-stream",
    )
