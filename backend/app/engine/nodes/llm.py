"""llm.prompt: the GenAI node. TODO Week 3.

Config example:
    {
      "prompt": "From these emails, list the urgent ones: {{n1.output.emails}}",
      "output_schema": {"urgent": "list[str]"},     # optional: ask for JSON in this shape
      "max_tokens": 500
    }

Output example:
    {"text": "...raw model reply...", "json": {"urgent": [...]}, "tokens_used": 312, "cost_usd": 0.0004}

TODO (Week 3), in this order:
  1. Call your LLM provider's API with the prompt (key from settings.llm_api_key).
     Wrap the call in asyncio.wait_for(..., timeout=settings.llm_timeout_seconds).
  2. If output_schema is given: tell the model to reply with ONLY JSON in that shape,
     then json.loads() the reply. If parsing fails, ask ONCE more ("Your reply was not valid
     JSON. Reply with only JSON."), and if it fails again raise ValueError so the executor
     records a failed step.
  3. Return text, json (or None), tokens_used and cost_usd. The executor copies tokens_used
     and cost_usd onto the StepRun row so the UI can show cost per step.
  4. Write a test with a FAKE client (never call the real API in tests): one that returns
     valid JSON, one that returns junk then valid JSON, one that times out.

Guardrails to explain in interviews: timeout, max_tokens, JSON validation, one repair retry.
"""

from typing import Any

from app.engine.nodes.base import Node, register


@register
class LLMPrompt(Node):
    type = "llm.prompt"

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("llm.prompt: see TODO in app/engine/nodes/llm.py")
