"""Crash recovery: the processing list, acks, and the reaper."""

import uuid
from datetime import UTC, datetime, timedelta

from app.engine.queue import ack_run, dequeue_run, enqueue_run, processing_name
from app.engine.reaper import requeue_stuck_runs
from app.models import Run, RunStatus, Workflow

NOW = datetime(2026, 11, 14, 18, 0, tzinfo=UTC)


async def make_run(db, status: RunStatus, started_minutes_ago: int) -> Run:
    wf = Workflow(name="t", graph={"nodes": [], "edges": []})
    db.add(wf)
    await db.flush()
    run = Run(workflow_id=wf.id, status=status, started_at=NOW - timedelta(minutes=started_minutes_ago))
    db.add(run)
    await db.commit()
    return run


async def test_queue_moves_the_id_to_processing(fresh_db_and_redis):
    run = uuid.uuid4()
    await enqueue_run(run)
    assert await dequeue_run(timeout=1) == run
    assert await fresh_db_and_redis.lrange(processing_name(), 0, -1) == [str(run)]


async def test_ack_removes_it_from_processing(fresh_db_and_redis):
    run = uuid.uuid4()
    await enqueue_run(run)
    await dequeue_run(timeout=1)
    await ack_run(run)
    assert await fresh_db_and_redis.llen(processing_name()) == 0


async def test_stuck_run_is_put_back_on_the_queue(db, fresh_db_and_redis):
    run = await make_run(db, RunStatus.RUNNING, started_minutes_ago=30)
    await enqueue_run(run.id)
    await dequeue_run(timeout=1)
    requeued = await requeue_stuck_runs(db, NOW)
    assert requeued == [run.id]
    assert run.status == RunStatus.QUEUED
    assert await fresh_db_and_redis.llen(processing_name()) == 0
    assert await dequeue_run(timeout=1) == run.id


async def test_finished_not_acked_is_just_cleaned_up(db, fresh_db_and_redis):
    run = await make_run(db, RunStatus.SUCCEEDED, started_minutes_ago=30)
    await enqueue_run(run.id)
    await dequeue_run(timeout=1)
    assert await requeue_stuck_runs(db, NOW) == []
    assert await fresh_db_and_redis.llen(processing_name()) == 0
    assert await fresh_db_and_redis.llen("flowpilot:runs") == 0


async def test_run_still_in_progress_is_left_alone(db, fresh_db_and_redis):
    run = await make_run(db, RunStatus.RUNNING, started_minutes_ago=2)
    await enqueue_run(run.id)
    await dequeue_run(timeout=1)
    assert await requeue_stuck_runs(db, NOW) == []
    assert await fresh_db_and_redis.llen(processing_name()) == 1
