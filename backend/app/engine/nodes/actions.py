"""Action nodes: the last blocks, which change something in the world. TODO Week 3.

action.http   Config: {"method": "POST", "url": "...", "json": {...}}
              Output: {"status_code": 200, "body": ...}
action.email  Config: {"to": "...", "subject": "...", "body": "..."}
              Output: {"sent": true, "message_id": "..."}
"""

from typing import Any

from app.engine.nodes.base import Node, register


@register
class HttpAction(Node):
    """TODO (Week 3):
    - Use httpx.AsyncClient with a timeout (e.g. 10s).
    - Raise an error for 5xx responses (so the executor retries them),
      but NOT for 4xx (a retry won't fix a bad request). How will you tell the executor that?
    - Test it with httpx.MockTransport, never a real URL.
    """

    type = "action.http"

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("action.http: see TODO in app/engine/nodes/actions.py")


@register
class EmailAction(Node):
    """TODO (Week 3):
    - Send with an email API (e.g. a transactional email service) or SMTP via aiosmtplib.
    - retryable = False: sending the same email twice is worse than failing once.
      In your README, explain this choice: it is the 'idempotency' interview question.
    """

    type = "action.email"
    retryable = False

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("action.email: see TODO in app/engine/nodes/actions.py")
