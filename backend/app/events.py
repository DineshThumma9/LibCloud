import time
from asyncio import Queue, Task
from fastapi.requests import Request
from .models import Event,Error

async def stream_events(queue: Queue, job_task: Task, request: Request):
    try:
        while True:
            if await request.is_disconnected():
                job_task.cancel()
                break

            event = await queue.get()

            yield f"data: {event.model_dump_json()}\n\n"

            if event.type and event.type in ("done", "error"):
                break

    except Exception as e:
        yield f"data: {Event(job_id='', type='error', ts=time.time(), seq=0, data=Error(phase='stream_error', message=str(e), retryable='false')).model_dump_json()}\n\n"
    finally:
        job_task.cancel()


class EventBus(Queue):
    """Queue carrying job events from the pipeline to the SSE stream."""
