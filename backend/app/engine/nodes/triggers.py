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
    """Config: {"cron": "0 8 * * *"} (every day at 08:00).The scheduler decides WHEN it runs."""

    type = "trigger.schedule"

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {"cron": config.get("cron"), "triggered_at": datetime.now(UTC).isoformat()}
