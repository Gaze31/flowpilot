"""Week 3: the LLM node, tested with FAKE models only (never the real API)."""

import asyncio

import pytest

from app.core.config import get_settings
from app.engine.nodes.llm import LLMPrompt, extract_json, set_llm_client


def fake_model(replies: list[str], calls: list[str]):
    """Returns an 'ask' function that answers with the given replies, in order."""

    async def ask(prompt: str, max_tokens: int) -> dict:
        calls.append(prompt)
        return {"text": replies[len(calls) - 1], "tokens_used": 10, "cost_usd": 0.001}

    return ask


@pytest.fixture(autouse=True)
def no_client_after_text():
    yield
    set_llm_client(None)


# Section 2 : extact_json
def test_extract_json_handles_fences():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a":1}\n```') == {"a": 1}
    with pytest.raises(ValueError):
        extract_json("Sure! Here you go")


async def test_valid_json_first_time():
    calls: list[str] = []
    set_llm_client(fake_model(['{"urgent": ["Server down!"]}'], calls))
    out = await LLMPrompt().run({"prompt": "List urgent", "output_schema": {"urgent": "list[str]"}}, {})
    assert out["json"] == {"urgent": ["Server down!"]}
    assert out["tokens_used"] == 10


# Section 3: the repair tests


async def test_junk_then_valid_json_repairs_once():
    calls: list[str] = []
    set_llm_client(fake_model(["Sure ! Here they are", '{"urgent": []}'], calls))
    out = await LLMPrompt().run({"prompt": "List urgent", "output_schema": {"urgent": "list[str]"}}, {})
    assert out["json"] == {"urgent": []}
    assert len(calls) == 2
    assert "Reply with only JSON" in calls[1]
    assert out["tokens_used"] == 20


async def test_junk_twice_fails():
    calls: list[str] = []
    set_llm_client(fake_model(["nope", "still nope"], calls))
    with pytest.raises(ValueError):
        await LLMPrompt().run({"prompt": "list urgent", "output_schema": {"urgent": "list[str]"}}, {})
    assert len(calls) == 2


# Section 4: no schema, and timeout


async def test_no_schema_returns_text_only():
    calls: list[str] = []
    set_llm_client(fake_model(["Hello there"], calls))
    out = await LLMPrompt().run({"prompt": "Say hi"}, {})
    assert out["text"] == "Hello there"
    assert out["json"] is None


async def test_slow_model_times_out(monkeypatch):
    async def slow(prompt: str, max_tokens: int) -> dict:
        await asyncio.sleep(1)
        return {"text": "{}", "tokens_used": 1, "cost_usd": 0.0}

    monkeypatch.setattr(get_settings(), "llm_timeout_seconds", 0.05)
    set_llm_client(slow)
    with pytest.raises(TimeoutError):
        await LLMPrompt().run({"prompt": "hi"}, {})
