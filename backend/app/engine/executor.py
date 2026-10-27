"""Runs one workflow, node by node, with retries and a log of every attempt. WEEK 2 TODO.

This is the file you'll be asked about most in interviews. The helpers at the top are done;
execute_run() is yours.
"""

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime  # noqa: F401
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.engine.graph import topological_sort  # noqa: F401
from app.engine.nodes import get_node  # noqa: F401
from app.engine.templating import render  # noqa: F401
from app.errors import NotFound  # noqa: F401
from app.models import Run, RunStatus, StepRun, StepStatus, Workflow  # noqa: F401

Sleep = Callable[[float], Awaitable[None]]


def backoff_seconds(attempt: int) -> float:
    """Wait before the NEXT try after `attempt` failed: 1s, 2s, 4s ... Done."""
    return get_settings().backoff_base_seconds * (2 ** (attempt - 1))


async def record_step(
    db: AsyncSession,
    run: Run,
    node: dict[str, Any],
    attempt: int,
    status: StepStatus,
    input_: dict[str, Any],
    started: float,
    output: dict[str, Any] | None = None,
    error: str | None = None,
) -> StepRun:
    """Save one attempt of one node. Done. `started` is time.perf_counter() from before the try."""
    step = StepRun(
        run_id=run.id,
        node_id=node["id"],
        node_type=node["type"],
        attempt=attempt,
        status=status,
        input=input_,
        output=output,
        error=error,
        duration_ms=int((time.perf_counter() - started) * 1000),
        tokens_used=(output or {}).get("tokens_used"),
        cost_usd=(output or {}).get("cost_usd"),
    )
    db.add(step)
    await db.commit()  # commit per attempt, so the UI can show progress live
    return step


async def execute_run(db: AsyncSession, run_id: uuid.UUID, sleep: Sleep = asyncio.sleep) -> Run:
    """Run every node of the run's workflow in order. Returns the finished Run.

    `sleep` is passed in so tests can replace it with a fake that doesn't really wait.

    TODO (Week 2), step by step:
      1. Load the Run (db.get(Run, run_id)); if None raise NotFound("run not found").
         Load its Workflow (db.get(Workflow, run.workflow_id)).
      2. Set run.status = RUNNING and run.started_at = datetime.now(UTC); commit.
      3. order = topological_sort(workflow.graph)
         nodes_by_id = {n["id"]: n for n in workflow.graph["nodes"]}
         context = {}   # filled as nodes finish: context[node_id] = {"output": output}
      4. For each node_id in order:
           node = nodes_by_id[node_id]; impl = get_node(node["type"])
           max_tries = settings.max_attempts if impl.retryable else 1
           for attempt in 1..max_tries:
               started = time.perf_counter()
               try:
                   config = render(node.get("config", {}), context)
                   output = await impl.run(config, context)
               except Exception as exc:   # record EVERY failed attempt
                   await record_step(..., StepStatus.FAILED, input_=<config if rendered else {}>,
                                     started=started, error=f"{type(exc).__name__}: {exc}")
                   if attempt < max_tries: await sleep(backoff_seconds(attempt)); continue
                   -> mark the run FAILED: run.error = f"node {node_id} failed: {exc}",
                      run.finished_at = now, commit, and return run (stop: later nodes don't run)
               else:
                   await record_step(..., StepStatus.SUCCEEDED, ..., output=output)
                   context[node_id] = {"output": output}
                   break
      5. All nodes done: run.status = SUCCEEDED, run.finished_at = now, commit, return run.

    Edge cases the tests check:
      - a node that fails twice then succeeds -> 3 step rows (fail, fail, ok) and sleeps of 1s and 2s
      - a node that always fails -> run FAILED after max_attempts, later nodes never run
      - a non-retryable node (retryable = False) is tried exactly once
      - templates: n2's config can use {{n1.output.x}}
    """
    raise NotImplementedError("execute_run: see TODO in app/engine/executor.py")
