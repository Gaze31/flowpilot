"""Week 3: the email action, tested with a fake sender(no real email is ever sent)."""

import pytest

from app.engine.executor import execute_run
from app.engine.nodes.actions import EmailAction, set_email_sender
from app.models import RunStatus
from tests.conftest import chain_graph
from tests.test_executor import make_run


def fake_sender(sent: list[tuple[str, str, str]], fail: bool = False):
    """A fake that records every email instead of sending it."""

    async def send(to: str, subject: str, body: str) -> str:
        sent.append((to, subject, body))
        if fail:
            raise RuntimeError("mail server down")
        return f"msg-{len(sent)}"

    return send


@pytest.fixture(autouse=True)
def no_sender_after_test():
    yield
    set_email_sender(None)


async def test_sends_email_and_returns_message_id():
    sent: list[tuple[str, str, str]] = []
    set_email_sender(fake_sender(sent))
    out = await EmailAction().run({"to": "me@example.com", "subject": "Urgent", "body": "Server down"}, {})
    assert out == {"sent": True, "message_id": "msg-1"}
    assert sent == [("me@example.com", "Urgent", "Server down")]


async def test_bad_address_is_rejected_before_sending():
    sent: list[tuple[str, str, str]] = []
    set_email_sender(fake_sender(sent))
    with pytest.raises(ValueError):
        await EmailAction().run({"to": "not-an-email"}, {})
    assert sent == []


async def test_no_sender_configured_fails_clearly():
    with pytest.raises(RuntimeError):
        await EmailAction().run({"to": "me@example.com"}, {})


async def test_failed_email_is_never_retried(db, fake_sleep, sleeps):
    sent: list[tuple[str, str, str]] = []
    set_email_sender(fake_sender(sent, fail=True))
    run_id = await make_run(db, chain_graph(("n1", "action.email", {"to": "me@example.com"})))
    run = await execute_run(db, run_id, sleep=fake_sleep)
    assert run.status == RunStatus.FAILED
    assert len(sent) == 1
    assert sleeps == []
