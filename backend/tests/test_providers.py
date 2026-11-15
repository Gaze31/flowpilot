"""The real providers: only the parts that don't need the internet."""

import pytest

from app.core.config import get_settings
from app.engine.nodes import actions, llm
from app.engine.providers import gemini_ask, log_email, parse_gemini, plug_in_providers


@pytest.fixture(autouse=True)
def unplug_after_test():
    yield
    llm.set_llm_client(None)
    actions.set_email_sender(None)


# Section 2
def test_parse_gemini_reads_text_and_tokens():
    data = {
        "candidates": [{"content": {"parts": [{"text": "Hello"}]}}],
        "usageMetadata": {"totalTokenCount": 12},
    }
    assert parse_gemini(data) == {"text": "Hello", "tokens_used": 12, "cost_usd": 0.0}


def test_parse_gemini_without_text_fails_clearly():
    with pytest.raises(RuntimeError):
        parse_gemini({"candidates": [{"finishReason": "MAX_TOKENS"}]})


# Section 3
async def test_log_email_returns_an_id():
    message_id = await log_email("me@example.com", "Hi", "Body")
    assert message_id.startswith("log-")


def test_plug_in_uses_gemini_when_a_key_is_set(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_api_key", "test-key")
    plug_in_providers()
    assert llm._ask is gemini_ask
    assert actions._send is log_email


def test_no_key_means_no_llm_client(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_api_key", None)
    plug_in_providers()
    assert llm._ask is None
    assert actions._send is log_email
