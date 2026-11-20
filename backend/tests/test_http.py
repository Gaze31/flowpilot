"""Week 3: the HTTP action, tested with httpx.MockTransport(never a real URL)."""

import httpx
import pytest

from app.engine.executor import execute_run
from app.engine.nodes.actions import HttpAction, set_http_transport
from app.errors import NonRetryableError
from app.models import RunStatus
from tests.conftest import chain_graph
from tests.test_executor import make_run


def fake_server(status: int, body, seen: list[httpx.Request]):
    """A fake server that records each request and answer with `status` and `body`."""

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if isinstance(body, str):
            return httpx.Response(status, text=body)
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
def no_transport_after_test():
    yield
    set_http_transport(None)


# Section 2: the node by itself


async def test_post_sends_json_and_returns_body():
    seen: list[httpx.Request] = []
    set_http_transport(fake_server(200, {"ok": True}, seen))
    out = await HttpAction().run({"method": "post", "url": "https://example.com/hook", "json": {"a": 1}}, {})
    assert out == {"status_code": 200, "body": {"ok": True}}
    assert seen[0].method == "POST"
    assert seen[0].url == "https://example.com/hook"
    assert seen[0].read() == b'{"a":1}'


async def test_plain_text_body_is_returned_as_text():
    seen: list[httpx.Request] = []
    set_http_transport(fake_server(200, "hello", seen))
    out = await HttpAction().run({"url": "https://example.com"}, {})
    assert out["body"] == "hello"
    assert seen[0].method == "GET"


async def test_server_error_is_retryable():
    seen: list[httpx.Request] = []
    set_http_transport(fake_server(503, {"error": "busy"}, seen))
    with pytest.raises(RuntimeError):
        await HttpAction().run({"url": "https://example.com"}, {})


async def test_client_error_is_not_retryable():
    seen: list[httpx.Request] = []
    set_http_transport(fake_server(404, {"error": "not found"}, seen))
    with pytest.raises(NonRetryableError):
        await HttpAction().run({"url": "https://example.com"}, {})


# Section 3 the exceutor really stops


async def test_executor_does_not_retry_a_4xx(db, fake_sleep, sleeps):
    seen: list[httpx.Request] = []
    set_http_transport(fake_server(404, {"error": "not found"}, seen))
    run_id = await make_run(db, chain_graph(("n1", "action.http", {"url": "https://example.com"})))
    run = await execute_run(db, run_id, sleep=fake_sleep)
    assert run.status == RunStatus.FAILED
    assert len(seen) == 1
    assert sleeps == []


async def test_keep_fields_trims_each_item_in_the_list():
    seen: list[httpx.Request] = []
    jobs = {
        "totalCount": 2,
        "jobs": [
            {"title": "Python Dev", "companyName": "A", "description": "very long text"},
            {"title": "Backend Eng", "companyName": "B", "description": "more long text"},
        ],
    }
    set_http_transport(fake_server(200, jobs, seen))
    out = await HttpAction().run({"url": "https://example.com", "list_key": "jobs", "keep_fields": ["title", "companyName"]}, {})
    assert out["body"] == {
        "jobs": [
            {"title": "Python Dev", "companyName": "A"},
            {"title": "Backend Eng", "companyName": "B"},
        ]
    }


async def test_keep_fields_works_on_a_top_level_list():
    seen: list[httpx.Request] = []
    set_http_transport(fake_server(200, [{"a": 1, "b": 2}], seen))
    out = await HttpAction().run({"url": "https://example.com", "keep_fields": ["a"]}, {})
    assert out["body"] == [{"a": 1}]


async def test_keep_fields_with_a_wrong_list_key_is_not_retryable():
    seen: list[httpx.Request] = []
    set_http_transport(fake_server(200, {"jobs": []}, seen))
    with pytest.raises(NonRetryableError):
        await HttpAction().run({"url": "https://example.com", "list_key": "results", "keep_fields": ["a"]}, {})
