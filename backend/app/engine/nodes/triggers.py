"""Trigger nodes: the first block of every workflow.

trigger.manual   Done. Passes its `payload` config straight through as output.
trigger.schedule TODO Week 3 (the node itself is trivial; the scheduler that fires it is the work).
"""

from datetime import UTC, datetime
from typing import Any

from app.engine.nodes.base import Node, register


@register
class ManualTrigger(Node):
    type = "trigger.manual"

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {"payload": config.get("payload", {}), "triggered_at": datetime.now(UTC).isoformat()}


@register
class ScheduleTrigger(Node):
    """Config: {"cron": "0 8 * * *"} (every day at 08:00).

    TODO (Week 3):
      The node's run() can just return {"triggered_at": ...} like ManualTrigger.
      The real work is a small scheduler process that, every minute, finds workflows whose
      trigger node is "trigger.schedule" and whose cron matches now, then creates a Run and
      enqueues it (same as POST /workflows/{id}/runs). Look at the `croniter` package.
      Question to answer in your README: what stops the scheduler from firing the same minute twice?
    """

    type = "trigger.schedule"

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("trigger.schedule: see TODO in app/engine/nodes/triggers.py")
