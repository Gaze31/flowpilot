"""A rescued run resumes where it stopped: steps that already succeeded are not run again."""

from sqlalchemy import select

from app.engine.executor import execute_run
from app.engine.nodes.actions import set_email_sender
from app.models import RunStatus, StepRun, StepStatus
from tests.conftest import chain_graph
from tests.test_email import fake_sender
from tests.test_executor import make_run


async def test_rescued_run_skips_step_that_already_succeeded(db, fake_sleep):
    sent: list[tuple[str, str, str]] = []
    set_email_sender(fake_sender(sent))
    run_id = await make_run(
        db,
        chain_graph(("n1", "action.email", {"to": "me@example.com"}), ("n2", "test.echo", {"done": True})),
    )
    db.add(
        StepRun(
            run_id=run_id,
            node_id="n1",
            node_type="action.email",
            attempt=1,
            status=StepStatus.SUCCEEDED,
            input={},
            output={"sent": True, "message_id": "msg-1"},
        )
    )
    await db.commit()

    run = await execute_run(db, run_id, sleep=fake_sleep)

    assert run.status == RunStatus.SUCCEEDED
    assert sent == []
    steps = (await db.scalars(select(StepRun).where(StepRun.run_id == run.id))).all()
    assert sorted(s.node_id for s in steps) == ["n1", "n2"]
