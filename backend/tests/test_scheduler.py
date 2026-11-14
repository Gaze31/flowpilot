# Section 1: imports and helpers

"""Week 3: the scheduler. Time is passed in, so tests never. wait for a real clock."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.engine.nodes.triggers import ScheduleTrigger
from app.engine.scheduler import fire_due_workflows, schedule_of
from app.models import Run, Workflow

EIGHT_AM = datetime(2026, 11, 14, 8, 0, 30, tzinfo=UTC)


def scheduled_graph(cron: str) -> dict:
    return {"nodes": [{"id": "n1", "type": "trigger.schedule", "config": {"cron": cron}}], "edges": []}


async def add_workflow(db, graph: dict) -> Workflow:
    wf = Workflow(name="t", graph=graph)
    db.add(wf)
    await db.commit()
    return wf


async def runs_in_db(db) -> list[Run]:
    return list((await db.scalars(select(Run))).all())


# Section 2 finding and firing


def test_schedule_of_finds_the_cron():
    assert schedule_of(scheduled_graph("0 8 * * *")) == "0 8 * * *"
    assert schedule_of({"nodes": [{"id": "n1", "type": "trigger.manual"}], "edges": []}) is None


async def test_due_workflow_is_queued(db, fresh_db_and_redis):
    await add_workflow(db, scheduled_graph("0 8 * * *"))
    started = await fire_due_workflows(db, EIGHT_AM)
    assert len(started) == 1
    runs = await runs_in_db(db)
    assert runs[0].trigger == "schedule"
    assert await fresh_db_and_redis.llen("flowpilot:runs") == 1


async def test_not_due_yet_does_nothing(db):
    await add_workflow(db, scheduled_graph("0 9 * * *"))
    assert await fire_due_workflows(db, EIGHT_AM) == []
    assert await runs_in_db(db) == []


# Section 3 : the importance  ones
async def test_same_minute_fires_only_once(db):
    await add_workflow(db, scheduled_graph("0 8 * * *"))
    first = await fire_due_workflows(db, EIGHT_AM)
    second = await fire_due_workflows(db, EIGHT_AM.replace(second=50))
    assert len(first) == 1
    assert second == []
    assert len(await runs_in_db(db)) == 1


async def test_bad_cron_skipped_not_crashed(db):
    await add_workflow(db, scheduled_graph("banana"))
    await add_workflow(db, scheduled_graph("0 8 * * *"))
    started = await fire_due_workflows(db, EIGHT_AM)
    assert len(started) == 1


async def test_scedule_trigger_node_output():
    out = await ScheduleTrigger().run({"cron": "0 8 * * *"}, {})
    assert out["cron"] == "0 8 * * *"
    assert "triggered_at" in out
