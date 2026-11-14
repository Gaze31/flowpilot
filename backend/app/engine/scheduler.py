"""The scheduler: once a minute, start every workflow whose schedule matches now.

Start it with: python -m app.engine.scheduler
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from croniter import croniter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.engine import queue
from app.models import Run, Workflow

log = logging.getLogger("flowpilot.scheduler")


def schedule_of(graph: dict[str, Any]) -> str | None:
    """The cron text of the workflow's schedule trigger, or None if it has none."""
    for node in graph.get("nodes", []):
        if node["type"] == "trigger.schedule":
            return node.get("config", {}).get("cron")
    return None


async def claim_minute(workflow_id: uuid.UUID, minute: datetime) -> bool:
    """True only for the FIRST caller for thi workflow and minute."""
    key = f"flowpilot:schedule:{workflow_id}:{minute:%Y%m%d%H%M}"
    return bool(await queue.get_redis().set(key, "1", nx=True, ex=120))


async def fire_due_workflows(db: AsyncSession, now: datetime) -> list[uuid.UUID]:
    minute = now.replace(second=0, microsecond=0)
    started: list[uuid.UUID] = []

    workflows = (await db.scalars(select(Workflow))).all()
    for wf in workflows:
        cron = schedule_of(wf.graph)
        if cron is None:
            continue
        try:
            due = croniter.match(cron, minute)
        except ValueError:
            log.warning("workflow %s has a bad cron: %r", wf.id, cron)
            continue
        if not due or not await claim_minute(wf.id, minute):
            continue

        run = Run(workflow_id=wf.id, trigger="schedule")
        db.add(run)
        await db.flush()
        await queue.enqueue_run(run.id)
        await db.commit()
        started.append(run.id)

    return started


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    log.info("scheduler started")
    while True:
        async with SessionLocal() as db:
            started = await fire_due_workflows(db, datetime.now(UTC))
        if started:
            log.info("started %d scheduled run(s)", len(started))
        await asyncio.sleep(60 - datetime.now(UTC).second)


if __name__ == "__main__":
    asyncio.run(main())
