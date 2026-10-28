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
    """
    settings = get_settings()

    # 1. Load the Run and its associated Workflow
    run = await db.get(Run, run_id)
    if run is None:
        raise NotFound("run not found")

    workflow = await db.get(Workflow, run.workflow_id)
    if workflow is None:
        raise NotFound("workflow not found")

    # 2. Set run status to RUNNING, mark start time, and commit state
    run.status = RunStatus.RUNNING
    run.started_at = datetime.now(UTC)
    await db.commit()

    # 3. Establish dependency sorting and context parameters
    order = topological_sort(workflow.graph)
    nodes_by_id = {n["id"]: n for n in workflow.graph["nodes"]}
    context = {}  # Filled dynamically: context[node_id] = {"output": output}

    # 4. Iterate over execution pipeline in dependency order
    for node_id in order:
        node = nodes_by_id[node_id]
        impl = get_node(node["type"])

        # Calculate max attempts based on node architecture type
        max_tries = settings.max_attempts if impl.retryable else 1

        # Guard config block initialization for exception safety tracking
        rendered_config = {}

        for attempt in range(1, max_tries + 1):
            started = time.perf_counter()
            try:
                # Dynamically compile configuration values from previous node outputs
                rendered_config = render(node.get("config", {}), context)
                output = await impl.run(rendered_config, context)

            except Exception as exc:
                # Record EVERY failed execution attempt distinctly
                await record_step(
                    db=db,
                    run=run,
                    node=node,
                    attempt=attempt,
                    status=StepStatus.FAILED,
                    input_=rendered_config,
                    started=started,
                    error=f"{type(exc).__name__}: {exc}",
                )

                # Check if we have more retries left in the quota
                if attempt < max_tries:
                    await sleep(backoff_seconds(attempt))
                    continue

                # Out of retries: Stop the workflow pipeline completely
                run.status = RunStatus.FAILED
                run.error = f"node {node_id} failed: {exc}"
                run.finished_at = datetime.now(UTC)
                await db.commit()
                return run

            else:
                # Successful execution trace recorded immediately
                await record_step(
                    db=db,
                    run=run,
                    node=node,
                    attempt=attempt,
                    status=StepStatus.SUCCEEDED,
                    input_=rendered_config,
                    started=started,
                    output=output,
                )

                # Cache the results inside context for downstream dependencies
                context[node_id] = {"output": output}
                break

    # 5. Pipeline completion reached successfully
    run.status = RunStatus.SUCCEEDED
    run.finished_at = datetime.now(UTC)
    await db.commit()

    return run
