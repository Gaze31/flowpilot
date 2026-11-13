"""llm.prompt: the GenAI node. Guardrails:timeout, JSON validation, one repair retry."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.config import get_settings
from app.engine.nodes.base import Node, register

AskFn = Callable[[str, int], Awaitable[dict[str, Any]]]

_ask: AskFn | None = None


def set_llm_client(ask: AskFn | None) -> None:
    global _ask
    _ask = ask


# Section 2 : Extract_json


def extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise ValueError("model did not return valid JSON") from None


# Section 3: call_llm, the timwout guard


async def call_llm(prompt: str, max_tokens: int) -> dict[str, Any]:
    if _ask is None:
        raise RuntimeError("no LLM client configured: call set_llm_client() first")
    timeout = get_settings().llm_timeout_seconds
    try:
        return await asyncio.wait_for(_ask(prompt, max_tokens), timeout=timeout)
    except TimeoutError:
        raise TimeoutError(f"model did not answer within{timeout}s") from None


# Section 4: the node itself


@register
class LLMPrompt(Node):
    type = "llm.prompt"

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        prompt = config["prompt"]
        max_tokens = config.get("max_tokens", 500)
        schema = config.get("output_schema")

        if schema is not None:
            prompt += f"\n\nReply with ONLY JSON in this shape: {json.dumps(schema)}"

        reply = await call_llm(prompt, max_tokens)
        tokens = reply["tokens_used"]
        cost = reply["cost_usd"]

        data = None
        if schema is not None:
            try:
                data = extract_json(reply["text"])
            except ValueError:
                reply = await call_llm(prompt + "\n\nYour reply was not valid JSON. Reply with only JSON.", max_tokens)
                tokens += reply["tokens_used"]
                cost += reply["cost_usd"]
                data = extract_json(reply["text"])
        return {"text": reply["text"], "json": data, "tokens_used": tokens, "cost_usd": cost}
