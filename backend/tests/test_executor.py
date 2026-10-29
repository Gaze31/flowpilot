"""Week 2: the executor. Order, templates, retries with backoff, failure handling."""

import uuid

import pytest
from sqlalchemy import select

from app.engine.executor import execute_run
from app.errors import NotFound
from app.models import Run, RunStatus, StepRun, StepStatus, Workflow
from tests.conftest import CALLS, chain_graph


async def make_run(db, graph) -> uuid.UUID:
    wf = Workflow(name="t", graph=graph)
    db.add(wf)
    await db.flush()
    run = Run(workflow_id=wf.id)
    db.add(run)
    await db.commit()
    return run.id


async def steps_of(db, run_id):
    return (await db.scalars(select(StepRun).where(StepRun.run_id == run_id).order_by(StepRun.created_at))).all()


async def test_success_passes_outputs_forward(db, fake_sleep):
    run_id = await make_run(
        db,
        chain_graph(
            ("n1", "trigger.manual", {"payload": {"name": "Mikasa"}}),
            ("n2", "test.echo", {"greeting": "Hi {{n1.output.payload.name}}"}),
        ),
    )
    run = await execute_run(db, run_id, sleep=fake_sleep)
    assert run.status == RunStatus.SUCCEEDED
    assert run.started_at is not None and run.finished_at is not None
    steps = await steps_of(db, run_id)
    assert [s.node_id for s in steps] == ["n1", "n2"]
    assert steps[1].output == {"greeting": "Hi Mikasa"}
    assert steps[1].input == {"greeting": "Hi Mikasa"}  # input is saved AFTER rendering


async def test_flaky_node_retries_with_backoff(db, fake_sleep, sleeps):
    run_id = await make_run(db, chain_graph(("n1", "test.flaky", {"fail_times": 2})))
    run = await execute_run(db, run_id, sleep=fake_sleep)
    assert run.status == RunStatus.SUCCEEDED
    steps = await steps_of(db, run_id)
    assert [(s.attempt, s.status) for s in steps] == [(1, StepStatus.FAILED), (2, StepStatus.FAILED), (3, StepStatus.SUCCEEDED)]
    assert sleeps == [1, 2]  # waited 1s then 2s
    assert "temporary failure #1" in steps[0].error


async def test_failing_node_stops_the_run(db, fake_sleep, sleeps):
    run_id = await make_run(db, chain_graph(("n1", "test.fail", {}), ("n2", "test.echo", {})))
    run = await execute_run(db, run_id, sleep=fake_sleep)
    assert run.status == RunStatus.FAILED
    assert "n1" in run.error
    steps = await steps_of(db, run_id)
    assert [s.node_id for s in steps] == ["n1", "n1", "n1"]  # 3 attempts, n2 never ran
    assert sleeps == [1, 2]  # no sleep after the last attempt


async def test_non_retryable_node_runs_once(db, fake_sleep, sleeps):
    run_id = await make_run(db, chain_graph(("n1", "test.fail_no_retry", {})))
    run = await execute_run(db, run_id, sleep=fake_sleep)
    assert run.status == RunStatus.FAILED
    assert CALLS["no_retry"] == 1
    assert sleeps == []


async def test_bad_template_fails_the_node(db, fake_sleep):
    run_id = await make_run(db, chain_graph(("n1", "test.echo", {"x": "{{ghost.output.y}}"})))
    run = await execute_run(db, run_id, sleep=fake_sleep)
    assert run.status == RunStatus.FAILED
    assert "TemplateError" in (await steps_of(db, run_id))[0].error


async def test_unknown_run_raises(db, fake_sleep):
    with pytest.raises(NotFound):
        await execute_run(db, uuid.uuid4(), sleep=fake_sleep)
