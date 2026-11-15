"""Try the real LLM step once: python demo_llm.py"""

import asyncio

from app.engine.nodes.llm import LLMPrompt
from app.engine.providers import plug_in_providers

EMAILS = [
    "Server is down! Customers can't log in.",
    "Lunch on Friday?",
    "CLient meeting moved to 10am tomorrow",
    "Weekly newsletter: 5 tips for productivity",
]


async def main() -> None:
    plug_in_providers()
    out = await LLMPrompt().run(
        {
            "prompt": f"From these emails, list the urgent ones: {EMAILS}",
            "output_schema": {"urgent": "list[str]"},
            "max_tokens": 2000,
        },
        {},
    )
    print("JSON: ", out["json"])
    print("Tokens:", out["tokens_used"])


if __name__ == "__main__":
    asyncio.run(main())
