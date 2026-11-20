"""Action nodes: the last blocks, which change something in the world.

action.http   Config: {"method": "POST", "url": "...", "json": {...},
                       "list_key": "jobs", "keep_fields": ["title", ...]}   (last two optional)
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


def keep_fields(body: Any, list_key: str | None, fields: list[str]) -> Any:
    """Keep only some fields of each item in a JSON list, so the next step gets a small input."""
    items = body.get(list_key) if list_key and isinstance(body, dict) else body
    if not isinstance(items, list):
        raise NonRetryableError(f"keep_fields: expected a list at '{list_key or 'the top level'}'")
    trimmed = [{f: item[f] for f in fields if f in item} for item in items if isinstance(item, dict)]
    return {list_key: trimmed} if list_key else trimmed


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

        fields = config.get("keep_fields")
        if fields:
            body = keep_fields(body, config.get("list_key"), fields)

        return {"status_code": response.status_code, "body": body}
