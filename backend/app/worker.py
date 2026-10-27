"""The worker process: takes runs off the queue and executes them. WEEK 2 TODO.

Start it with:  python -m app.worker
In docker-compose it runs as its own service next to the API. Run 2 of them to see
two runs execute at the same time (that's horizontal scaling, an interview favourite).
"""

import asyncio
import logging

from app.db.session import SessionLocal  # noqa: F401
from app.engine.executor import execute_run  # noqa: F401
from app.engine.queue import dequeue_run  # noqa: F401

log = logging.getLogger("flowpilot.worker")


async def process_one(timeout: int = 5) -> bool:
    """Take ONE run from the queue and execute it. Return True if a run was processed.

    TODO (Week 2):
      run_id = await dequeue_run(timeout)
      if run_id is None: return False
      async with SessionLocal() as db:
          try: await execute_run(db, run_id)
          except Exception: log.exception(...)   # one bad run must never kill the worker
      return True
    """
    raise NotImplementedError("process_one: see TODO in app/worker.py")


async def main() -> None:
    """Loop forever. Done (once process_one works)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    log.info("worker started, waiting for runs")
    while True:
        await process_one()


if __name__ == "__main__":
    asyncio.run(main())
