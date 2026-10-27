"""Start a run and read run history. Done (the parts it calls are your TODOs).

POST /workflows/{id}/runs
  1. checks the graph has a valid order  -> your topological_sort() (422 if there's a cycle)
  2. creates a Run row with status=queued
  3. puts its id on the Redis queue      -> your enqueue_run()
  4. replies 202 straight away. The worker does the slow part later.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.workflows import get_workflow_or_404
from app.db.session import get_db
from app.engine import queue
from app.engine.graph import topological_sort
from app.errors import NotFound
from app.models import Run
from app.schemas import RunDetail, RunOut

router = APIRouter(tags=["runs"])


@router.post("/workflows/{workflow_id}/runs", response_model=RunOut, status_code=status.HTTP_202_ACCEPTED)
async def start_run(workflow_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    wf = await get_workflow_or_404(db, workflow_id)
    topological_sort(wf.graph)  # raises CycleError -> 422 before anything is queued
    run = Run(workflow_id=wf.id, trigger="manual")
    db.add(run)
    await db.flush()  # gives run.id without committing yet
    await queue.enqueue_run(run.id)
    await db.commit()  # only commit once it's safely on the queue
    await db.refresh(run)
    return run


@router.get("/workflows/{workflow_id}/runs", response_model=list[RunOut])
async def list_runs(workflow_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await get_workflow_or_404(db, workflow_id)
    result = await db.scalars(select(Run).where(Run.workflow_id == workflow_id).order_by(Run.created_at.desc()).limit(50))
    return result.all()


@router.get("/runs/{run_id}", response_model=RunDetail)
async def get_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    run = await db.scalar(select(Run).where(Run.id == run_id).options(selectinload(Run.steps)))
    if run is None:
        raise NotFound("run not found")
    return run
