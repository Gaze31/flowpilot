"""Real connections for the LLM and email steps. Plugged in once, when the worker starts.

Tests never use these: they plug in fakes instead.
"""

import logging
import uuid
from typing import Any

import httpx

from app.core.config import get_settings
from app.engine.nodes.actions import set_email_sender
from app.engine.nodes.llm import set_llm_client
from app.errors import NonRetryableError

log = logging.getLogger("flowpilot.providers")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RESEND_URL = "https://api.resend.com/emails"

# Section 2


def parse_gemini(data: dict[str, Any]) -> dict[str, Any]:
    """Turn Gemini's JSON reply into the shape the LLM step expects."""
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"model returned no text: {data}") from None
    tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
    return {"text": text, "tokens_used": tokens, "cost_usd": 0.0}


# Section 3
async def gemini_ask(prompt: str, max_tokens: int) -> dict[str, Any]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            GEMINI_URL.format(model=settings.llm_model),
            headers={"x-goog-api-key": settings.llm_api_key or ""},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens},
            },
        )
    if response.status_code >= 500:
        raise RuntimeError(f"Gemini server error {response.status_code}: {response.text[:300]}")
    if response.status_code >= 400:
        raise NonRetryableError(f"Gemini rejected the request({response.status_code}): {response.text}")

    return parse_gemini(response.json())


# Section 4
async def log_email(to: str, subject: str, body: str) -> str:
    """Prints the email to the log instead of sending it. Safe for demos."""
    message_id = f"log-{uuid.uuid4().hex[:8]}"
    log.info("EMAIL to=%s subject=%r id=%s\n%s", to, subject, message_id, body)
    return message_id


def _http_client() -> httpx.AsyncClient:
    """One place that builds the client for Resend, so tests can swap in a MockTransport."""
    return httpx.AsyncClient(timeout=get_settings().email_timeout_seconds)


async def resend_email(to: str, subject: str, body: str) -> str:
    """Sends a real email through Resend and returns Resend's message id."""
    settings = get_settings()
    async with _http_client() as client:
        response = await client.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key or ''}"},
            json={"from": settings.email_from, "to": to, "subject": subject, "text": body},
        )
    if response.status_code >= 500:
        raise RuntimeError(f"Resend server error {response.status_code}: {response.text[:300]}")
    if response.status_code >= 400:
        raise NonRetryableError(f"Resend rejected the email ({response.status_code}): {response.text[:300]}")
    try:
        return str(response.json()["id"])
    except (KeyError, ValueError, TypeError):
        raise RuntimeError(f"Resend reply had no message id: {response.text[:300]}") from None


def plug_in_providers() -> None:
    settings = get_settings()
    if settings.llm_api_key:
        set_llm_client(gemini_ask)
        log.info("LLM:Gemini, model %s", settings.llm_model)
    else:
        log.warning("LLM_API_KEY is not set, so llm.prompt steps will fail")
    if settings.resend_api_key:
        set_email_sender(resend_email)
        log.info("Email: Resend, from %s", settings.email_from)
    else:
        set_email_sender(log_email)
        log.warning("RESEND_API_KEY is not set, so emails are only written to the log")
