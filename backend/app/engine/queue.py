"""The job queue between the API and the worker. WEEK 2 TODO.

Why a queue? The API must reply in milliseconds, but a workflow can take seconds or
minutes (LLM calls, retries with waits). So the API only drops the run id into Redis,
and a separate worker process picks it up. Several workers can share one queue.

We use a plain Redis LIST (no extra library), so you can see exactly what happens:
    enqueue: LPUSH queue_name run_id      (add to the left end)
    dequeue: BRPOP queue_name timeout     (take from the right end; waits if empty)
LPUSH + BRPOP = first in, first out.
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


async def enqueue_run(run_id: uuid.UUID) -> None:
    """TODO (Week 2): LPUSH the run id (as a string) onto settings.queue_name."""
    settings = get_settings()
    redis_client = get_redis()

    # LPUSH the run id as a string to the left end of the list
    await redis_client.lpush(settings.queue_name, str(run_id))


async def dequeue_run(timeout: int = 5) -> uuid.UUID | None:
    """Wait up to `timeout` seconds for the next run id.

    TODO (Week 2): BRPOP settings.queue_name with the timeout.
      - It returns None if nothing arrived in time -> return None.
      - Otherwise it returns (queue_name, value) -> return uuid.UUID(value).
    """
    settings = get_settings()
    redis_client = get_redis()

    # BRPOP blocks until an item is available or the timeout is hit
    result = await redis_client.brpop(settings.queue_name, timeout)

    # If the timeout expires without an item, Redis returns None
    if result is None:
        return None

    # BRPOP returns a tuple: (queue_name, value)
    _, value = result

    # Convert the string value back into a uuid.UUID object
    return uuid.UUID(value)
