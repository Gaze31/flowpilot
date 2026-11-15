"""The repear: puts runs back on the queue when the worker running them has died."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import queue
from app.models import Run, RunStatus

log = logging.getLogger("flowpilot.reaper")

STUCK_AFTER = timedelta(minutes=15)


def as_utc(moment: datetime) -> datetime:
    """SQLite gives back times without a timezone. Treat those as UTC so we can compare them."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment


async def requeue_stuck_runs(db: AsyncSession, now: datetime, stuck_after: timedelta = STUCK_AFTER) -> list[uuid.UUID]:
    redis = queue.get_redis()
    processing = queue.processing_name()
    requeued: list[uuid.UUID] = []

    for value in await redis.lrange(processing, 0, -1):
        run = await db.get(Run, uuid.UUID(value))

        if run is None or run.status in (RunStatus.SUCCEEDED, RunStatus.FAILED):
            await redis.lrem(processing, 1, value)
            continue

        since = as_utc(run.started_at or run.created_at)
        if now - since < stuck_after:
            continue

        log.warning("run %s looks stuck since %s, putting it back on the queue", run.id, since)
        run.status = RunStatus.QUEUED
        run.started_at = None
        await db.commit()
        await redis.lrem(processing, 1, value)
        await queue.enqueue_run(run.id)
        requeued.append(run.id)

    return requeued
