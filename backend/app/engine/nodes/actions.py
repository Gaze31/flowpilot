"""Action nodes: the last blocks, which change something in the world. TODO Week 3.

action.http   Config: {"method": "POST", "url": "...", "json": {...}}
              Output: {"status_code": 200, "body": ...}
action.email  Config: {"to": "...", "subject": "...", "body": "..."}
              Output: {"sent": true, "message_id": "..."}
"""

from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from app.engine.nodes.base import Node, register
from app.errors import NonRetryableError

SendFn = Callable[[str, str, str], Awaitable[str]]
_send: SendFn | None = None


def set_email_sender(send: SendFn | None) -> None:
    """Plug in the function that really sends email. Tests plug in a fake one."""
    global _send
    _send = send


@register
class EmailAction(Node):
    type = "action.email"
    retryable = False

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        to = config["to"]
        subject = config.get("subject", "")
        body = config.get("body", "")

        if "@" not in to:
            raise ValueError(f"not a valid email address: {to}")
        if _send is None:
            raise RuntimeError("no email sender configured: call set_email_sender() first")

        message_id = await _send(to, subject, body)
        return {"sent": True, "message_id": message_id}


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
