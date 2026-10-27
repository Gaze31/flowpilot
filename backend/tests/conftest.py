"""Test setup. Done.

- Uses SQLite in a temp file (no Postgres needed to run tests) and a fake in-memory Redis.
- Registers 4 tiny test-only node types so executor tests don't need real LLMs or emails.
- `todo` marks tests for code you haven't written yet (see README: "How the tests guide you").
"""

import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}/test.db"
os.environ["DB_NULL_POOL"] = "true"
os.environ["BACKOFF_BASE_SECONDS"] = "1"
os.environ["MAX_ATTEMPTS"] = "3"

from typing import Any  # noqa: E402

import fakeredis  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.engine import queue  # noqa: E402
from app.engine.nodes.base import Node, register  # noqa: E402
from app.main import app  # noqa: E402


def todo(week: int, what: str):
    """xfail while the TODO raises NotImplementedError; FAIL if it's implemented wrong;
    XPASS(strict) once it's right -> then delete the marker from the test."""
    return pytest.mark.xfail(raises=NotImplementedError, strict=True, reason=f"TODO week {week}: {what}")


def raise_if_todo(resp) -> None:
    """API routes turn NotImplementedError into HTTP 501. Turn it back so `todo` sees it."""
    if resp.status_code == 501:
        raise NotImplementedError(resp.json()["detail"])


# ---------- test-only node types ----------
CALLS: dict[str, int] = {}


@register
class EchoNode(Node):
    """Returns its (already rendered) config as output."""

    type = "test.echo"

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return dict(config)


@register
class FlakyNode(Node):
    """Fails config['fail_times'] times, then succeeds."""

    type = "test.flaky"

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        key = config.get("key", "flaky")
        CALLS[key] = CALLS.get(key, 0) + 1
        if CALLS[key] <= config.get("fail_times", 0):
            raise RuntimeError(f"temporary failure #{CALLS[key]}")
        return {"ok": True, "calls": CALLS[key]}


@register
class FailNode(Node):
    type = "test.fail"

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("always fails")


@register
class FailOnceOnlyNode(Node):
    """Not retryable: must be tried exactly once."""

    type = "test.fail_no_retry"
    retryable = False

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        CALLS["no_retry"] = CALLS.get("no_retry", 0) + 1
        raise RuntimeError("must not be retried")


# ---------- fixtures ----------
@pytest.fixture(autouse=True)
async def fresh_db_and_redis():
    CALLS.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    fake = fakeredis.FakeAsyncRedis(decode_responses=True)
    queue.set_redis(fake)
    yield fake
    await fake.aclose()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def db():
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def fake_sleep(sleeps):
    async def _sleep(seconds: float) -> None:
        sleeps.append(seconds)

    return _sleep


def chain_graph(*nodes: tuple[str, str, dict]) -> dict:
    """chain_graph(("n1","test.echo",{}), ("n2","test.echo",{})) -> n1 -> n2"""
    return {
        "nodes": [{"id": i, "type": t, "config": c} for i, t, c in nodes],
        "edges": [{"source": a[0], "target": b[0]} for a, b in zip(nodes, nodes[1:], strict=False)],
    }
