"""The worker process: takes runs off the queue and executes them. WEEK 2 TODO.

Start it with:  python -m app.worker
In docker-compose it runs as its own service next to the API. Run 2 of them to see
two runs execute at the same time (that's horizontal scaling, an interview favourite).
"""

import asyncio
import logging

from app.db.session import SessionLocal  # noqa: F401
from app.engine.executor import execute_run  # noqa: F401
from app.engine.queue import dequeue_run

log = logging.getLogger("flowpilot.worker")


async def process_one(timeout: int = 5) -> bool:
    """Take one run from the queue and execute it. Returns True if a run was processed."""
    # take the run_id frm queue
    run_id = await dequeue_run(timeout)
    if run_id is None:
        log.info("no runs in queue, waiting...")
        return False
    async with SessionLocal() as db:
        try:
            log.info("starting run %s", run_id)
            await execute_run(db, run_id)
            log.info("finished run %s", run_id)
        except Exception:
            log.exception("run %s crashed", run_id)

        return True


async def main() -> None:
    """Loop forever. Done (once process_one works)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    log.info("worker started, waiting for runs")
    while True:
        await process_one()


if __name__ == "__main__":
    asyncio.run(main())
