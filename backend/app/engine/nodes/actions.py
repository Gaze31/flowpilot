"""Action nodes: the last blocks, which change something in the world. TODO Week 3.

action.http   Config: {"method": "POST", "url": "...", "json": {...}}
              Output: {"status_code": 200, "body": ...}
action.email  Config: {"to": "...", "subject": "...", "body": "..."}
              Output: {"sent": true, "message_id": "..."}
"""

from typing import Any

import httpx

from app.engine.nodes.base import Node, register
from app.errors import NonRetryableError

_transport: httpx.AsyncBaseTransport | None = None


def set_http_transport(transport: httpx.AsyncBaseTransport | None) -> None:
    """Tests plug in httpx.MockTransport here, so no real request is ever sent."""
    global _transport
    _transport = transport


@register
class HttpAction(Node):
    type = "action.http"

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        method = config.get("method", "GET").upper()
        url = config["url"]

        async with httpx.AsyncClient(timeout=10.0, transport=_transport) as client:
            response = await client.request(method, url, json=config.get("json"))

        if response.status_code >= 500:
            raise RuntimeError(f"server error{response.status_code} from {url}")
        if response.status_code >= 400:
            raise NonRetryableError(f"request rejected with{response.status_code} from {url}")

        try:
            body = response.json()
        except ValueError:
            body = response.text

        return {"status_code": response.status_code, "body": body}


@register
class EmailAction(Node):
    """Sends an email.Done tomorrow."""

    type = "action.email"
    retryable = False

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("action.email:coming next")
