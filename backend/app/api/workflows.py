"""Workflow CRUD. Done: read it, it's the pattern every other route follows."""

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.errors import NotFound
from app.models import Workflow
from app.schemas import WorkflowCreate, WorkflowOut, WorkflowUpdate

router = APIRouter(prefix="/workflows", tags=["workflows"])


async def get_workflow_or_404(db: AsyncSession, workflow_id: uuid.UUID) -> Workflow:
    wf = await db.get(Workflow, workflow_id)
    if wf is None:
        raise NotFound("workflow not found")
    return wf


@router.post("", response_model=WorkflowOut, status_code=status.HTTP_201_CREATED)
async def create_workflow(body: WorkflowCreate, db: AsyncSession = Depends(get_db)):
    wf = Workflow(name=body.name, graph=body.graph.model_dump())
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return wf


@router.get("", response_model=list[WorkflowOut])
async def list_workflows(db: AsyncSession = Depends(get_db)):
    result = await db.scalars(select(Workflow).order_by(Workflow.created_at.desc()))
    return result.all()


@router.get("/{workflow_id}", response_model=WorkflowOut)
async def get_workflow(workflow_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await get_workflow_or_404(db, workflow_id)


@router.patch("/{workflow_id}", response_model=WorkflowOut)
async def update_workflow(workflow_id: uuid.UUID, body: WorkflowUpdate, db: AsyncSession = Depends(get_db)):
    wf = await get_workflow_or_404(db, workflow_id)
    if body.name is not None:
        wf.name = body.name
    if body.graph is not None:
        wf.graph = body.graph.model_dump()
    await db.commit()
    await db.refresh(wf)
    return wf


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    wf = await get_workflow_or_404(db, workflow_id)
    await db.delete(wf)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
