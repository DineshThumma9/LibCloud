import asyncio

import pytest

from app.events import Event, EventBus, stream_events


class FakeRequest:
    async def is_disconnected(self) -> bool:
        return False


@pytest.mark.anyio
async def test_stream_events_reads_from_event_bus():
    bus = EventBus()
    await bus.put(Event(job_id="job", type="done", ts=0, seq=0, data={}))

    job_task = asyncio.create_task(asyncio.sleep(60))
    chunks = [chunk async for chunk in stream_events(bus, job_task, FakeRequest())]

    assert chunks == [
        'data: {"job_id":"job","type":"done","ts":0.0,"seq":0,"data":{}}\n\n'
    ]

    with pytest.raises(asyncio.CancelledError):
        await job_task
