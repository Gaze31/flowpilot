"""Week 2: the Redis queue (runs against an in-memory fake Redis)."""

import uuid

from app.engine.queue import dequeue_run, enqueue_run
from tests.conftest import todo


@todo(2, "queue.enqueue_run / dequeue_run")
async def test_first_in_first_out():
    a, b = uuid.uuid4(), uuid.uuid4()
    await enqueue_run(a)
    await enqueue_run(b)
    assert await dequeue_run(timeout=1) == a
    assert await dequeue_run(timeout=1) == b


@todo(2, "queue.dequeue_run")
async def test_empty_queue_returns_none():
    assert await dequeue_run(timeout=1) is None
