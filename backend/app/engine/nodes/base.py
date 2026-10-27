"""What every node type looks like, plus the registry. Done.

A node is a small class with:
  - type: a unique string, e.g. "trigger.manual" (this is what the graph JSON stores)
  - run(config, context) -> dict : does the work and returns its OUTPUT

`config`  = the node's settings from the graph, with {{templates}} already filled in
`context` = outputs of earlier nodes, e.g. {"n1": {"output": {...}}}

Register a node with @register so the API and the executor can find it by its type.
"""

from typing import Any, ClassVar

REGISTRY: dict[str, type["Node"]] = {}


class Node:
    type: ClassVar[str]
    retryable: ClassVar[bool] = True  # set False for nodes that must never run twice (e.g. sending money)

    async def run(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


def register(cls: type[Node]) -> type[Node]:
    REGISTRY[cls.type] = cls
    return cls


def get_node(node_type: str) -> Node:
    try:
        return REGISTRY[node_type]()
    except KeyError:
        raise ValueError(f"unknown node type: {node_type}") from None
