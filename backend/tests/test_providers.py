"""The real providers: only the parts that don't need the internet."""

import json
import logging

import httpx
import pytest

from app.core.config import DEFAULT_EMAIL_FROM, Settings, get_settings
from app.engine import providers
from app.engine.nodes import actions, llm
from app.engine.providers import gemini_ask, log_email, parse_gemini, plug_in_providers, resend_email
from app.errors import NonRetryableError


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
    monkeypatch.setattr(get_settings(), "resend_api_key", None)
    plug_in_providers()
    assert llm._ask is gemini_ask
    assert actions._send is log_email


def test_no_key_means_no_llm_client(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_api_key", None)
    monkeypatch.setattr(get_settings(), "resend_api_key", None)
    plug_in_providers()
    assert llm._ask is None
    assert actions._send is log_email


# Resend (email), tested with httpx.MockTransport only: no real API calls
def use_resend_transport(monkeypatch, handler, seen=None):
    monkeypatch.setattr(get_settings(), "resend_api_key", "re_fake_key")
    monkeypatch.setattr(get_settings(), "email_from", "FlowPilot <onboarding@resend.dev>")

    def handle(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return handler(request)

    monkeypatch.setattr(providers, "_http_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handle)))


async def test_resend_sends_the_right_request_and_returns_the_id(monkeypatch):
    seen: list[httpx.Request] = []
    use_resend_transport(monkeypatch, lambda r: httpx.Response(200, json={"id": "msg_123"}), seen)

    message_id = await resend_email("me@example.com", "Hi", "Body")

    assert message_id == "msg_123"
    request = seen[0]
    assert request.method == "POST"
    assert str(request.url) == "https://api.resend.com/emails"
    assert request.headers["Authorization"] == "Bearer re_fake_key"
    assert json.loads(request.content) == {
        "from": "FlowPilot <onboarding@resend.dev>",
        "to": "me@example.com",
        "subject": "Hi",
        "text": "Body",
    }


async def test_resend_4xx_is_not_retried(monkeypatch):
    use_resend_transport(monkeypatch, lambda r: httpx.Response(422, json={"message": "bad address"}))
    with pytest.raises(NonRetryableError):
        await resend_email("nope", "Hi", "Body")


async def test_resend_5xx_is_a_normal_retryable_error(monkeypatch):
    use_resend_transport(monkeypatch, lambda r: httpx.Response(503, text="down"))
    with pytest.raises(RuntimeError) as info:
        await resend_email("me@example.com", "Hi", "Body")
    assert not isinstance(info.value, NonRetryableError)


async def test_resend_timeout_raises_a_plain_error(monkeypatch):
    def slow(request):
        raise httpx.ReadTimeout("too slow", request=request)

    use_resend_transport(monkeypatch, slow)
    with pytest.raises(httpx.ReadTimeout):
        await resend_email("me@example.com", "Hi", "Body")


def test_plug_in_uses_resend_only_when_its_key_is_set(monkeypatch):
    monkeypatch.setattr(get_settings(), "resend_api_key", "re_fake_key")
    plug_in_providers()
    assert actions._send is resend_email

    monkeypatch.setattr(get_settings(), "resend_api_key", None)
    plug_in_providers()
    assert actions._send is log_email


def test_resend_key_never_appears_in_logs(monkeypatch, caplog):
    fake_key = "re_super_secret_fake_key_123"
    monkeypatch.setattr(get_settings(), "resend_api_key", fake_key)
    monkeypatch.setattr(get_settings(), "llm_api_key", None)
    with caplog.at_level(logging.DEBUG):
        plug_in_providers()

    assert actions._send is resend_email
    assert any("Resend" in record.getMessage() for record in caplog.records)  # it did log something
    assert fake_key not in caplog.text
    assert all(fake_key not in record.getMessage() for record in caplog.records)


def test_blank_email_from_falls_back_to_the_default():
    assert Settings(email_from="").email_from == DEFAULT_EMAIL_FROM
