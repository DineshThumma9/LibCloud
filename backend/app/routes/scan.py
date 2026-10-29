import asyncio
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.events import stream_events
from app.jobs import JobManager
from app.services.pipeline import run_pipeline

router = APIRouter()


@router.api_route("/libcloud", methods=["GET", "POST"])
async def libcloud(
    username: str,
    request: Request,
    token: Optional[str] = None,
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
