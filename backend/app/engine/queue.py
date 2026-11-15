"""The job queue between the API and the worker. Done.

Why a queue? The API must reply in milliseconds, but a workflow can take seconds or
minutes (LLM calls, retries with waits). So the API only drops the run id into Redis,
and a separate worker process picks it up. Several workers can share one queue.

Two Redis lists:
enqueue: LPUSH queue run_id                  (add to the left end)
dequeue: BLMOVE queue -> processing (atomic) (take from the right end)
ack: LREM processing run_id                   (the run is finished)
If a worker dies mid-run, its run id stays in `processing`, so the reaper can find it.
"""

import uuid

from redis.asyncio import Redis

from app.core.config import get_settings

_client: Redis | None = None


def get_redis() -> Redis:
    """One shared client per process. Tests replace it with a fake Redis via set_redis()."""
    global _client
    if _client is None:
        _client = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _client


def set_redis(client: Redis) -> None:
    global _client
    _client = client


def processing_name() -> str:
    """The second list: run ids a worker has taken but not finished yet."""
    return f"{get_settings().queue_name}: processing"


async def enqueue_run(run_id: uuid.UUID) -> None:
    """Add a run id to the left end of the queue."""
    settings = get_settings()
    redis_client = get_redis()
    # LPUSH the run id as a string to the left end of the list
    await redis_client.lpush(settings.queue_name, str(run_id))


async def dequeue_run(timeout: int = 5) -> uuid.UUID | None:
    """wait up to `timeout` seconds for the next run id, and MOVE it to the processing list.

    Returns None if nothing arrived in time.
    """
    settings = get_settings()
    redis_client = get_redis()
    # BLMOVE: take from the right end of the queue and put it on the processing list,
    # in one atomic step, so the run id is never lost between the two lists
    value = await redis_client.blmove(settings.queue_name, processing_name(), timeout, "RIGHT", "LEFT")

    if value is None:
        return None

    return uuid.UUID(value)


async def ack_run(run_id: uuid.UUID) -> None:
    """The run is finished: remove it from the processing list."""
    await get_redis().lrem(processing_name(), 1, str(run_id))
