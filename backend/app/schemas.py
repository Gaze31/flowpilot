"""Request/response shapes. Done.

The Graph validator checks the SHAPE of a drawing (unique ids, edges point at real nodes,
known node types). It does NOT check for cycles: that is your topological_sort() in
app/engine/graph.py, called when a run starts.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.engine.nodes import REGISTRY
from app.models import RunStatus, StepStatus


class NodeIn(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_]{1,64}$")
    type: str
    config: dict[str, Any] = Field(default_factory=dict)
    position: dict[str, float] | None = None  # x/y on the canvas; the backend ignores it


class EdgeIn(BaseModel):
    source: str
    target: str


class Graph(BaseModel):
    nodes: list[NodeIn] = Field(min_length=1)
    edges: list[EdgeIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_shape(self) -> "Graph":
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("node ids must be unique")
        unknown = sorted({n.type for n in self.nodes} - REGISTRY.keys())
        if unknown:
            raise ValueError(f"unknown node types: {unknown}")
        known = set(ids)
        for e in self.edges:
            if e.source not in known or e.target not in known:
                raise ValueError(f"edge {e.source}->{e.target} points at a node that doesn't exist")
            if e.source == e.target:
                raise ValueError(f"node {e.source} can't connect to itself")
        return self


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    graph: Graph


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    graph: Graph | None = None


class WorkflowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    graph: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class StepRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    node_id: str
    node_type: str
    attempt: int
    status: StepStatus
    input: dict[str, Any]
    output: dict[str, Any] | None
    error: str | None
    duration_ms: int
    tokens_used: int | None
    cost_usd: float | None
    created_at: datetime


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workflow_id: uuid.UUID
    status: RunStatus
    trigger: str
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class RunDetail(RunOut):
    steps: list[StepRunOut]
