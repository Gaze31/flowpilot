"""Running order of a workflow. WEEK 1 TODO: this is the heart of the engine.

A workflow is a DAG (directed acyclic graph): blocks are nodes, arrows are edges.
To run it we need an order where every node comes AFTER all the nodes that feed into it.
That order is called a topological sort.

    n1 (trigger) --> n2 (llm) --> n4 (email)
              \\--> n3 (http) --/

    Valid orders: [n1, n2, n3, n4] or [n1, n3, n2, n4]. Never n4 before n2 or n3.

If the graph has a loop (n2 -> n3 -> n2) there is no valid order: raise CycleError.
"""

from collections import deque  # noqa: F401  (you'll want this)
from typing import Any

from app.errors import CycleError  # noqa: F401  (you'll raise this)


def topological_sort(graph: dict[str, Any]) -> list[str]:
    """Return node ids in a valid running order.

    `graph` looks like:
        {"nodes": [{"id": "n1", ...}, {"id": "n2", ...}],
         "edges": [{"source": "n1", "target": "n2"}]}

    TODO (Week 1): implement Kahn's algorithm. Write it yourself; interviewers ask about this.
      1. in_degree: for every node id, count how many edges point INTO it (start all at 0).
         children: for every node id, the list of nodes it points to.
      2. Put every node with in_degree 0 into a queue, in the order they appear in
         graph["nodes"] (this makes the result deterministic, so tests can check it exactly).
      3. While the queue isn't empty: pop from the left, append to `order`,
         and for each child: in_degree[child] -= 1; if it hits 0, append the child to the queue.
      4. If len(order) < number of nodes, some nodes were never freed: that means a cycle.
         raise CycleError(f"workflow has a cycle involving: {sorted(stuck_node_ids)}")
      5. return order

    Complexity to say in interviews: O(V + E) time, O(V) extra space.
    """
    node_ids = [node["id"] for node in graph.get("nodes", [])]
    in_degree = {node_id: 0 for node_id in node_ids}
    children = {node_id: [] for node_id in node_ids}

    for edge in graph.get("edges", []):
        source = edge["source"]
        target = edge["target"]
        if source not in children or target not in in_degree:
            raise ValueError(f"edge {source}->{target} points at an unknown node")
        children[source].append(target)
        in_degree[target] += 1

    queue = deque([node_id for node_id in node_ids if in_degree[node_id] == 0])
    order = []

    while queue:
        current = queue.popleft()
        order.append(current)

        for child in children[current]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if len(order) < len(node_ids):
        stuck_node_ids = [node_id for node_id, deg in in_degree.items() if deg > 0]
        raise CycleError(f"workflow has a cycle; these nodes are in it or blocked by it: {sorted(stuck_node_ids)}")
    return order


def upstream_of(graph: dict[str, Any], node_id: str) -> set[str]:
    """Return every node that `node_id` depends on, directly or indirectly.

    Used in Week 2 to check a template only references nodes that run BEFORE it:
    {{n4.output.x}} inside n2 is invalid if n4 runs after n2.

    TODO (Week 1, after topological_sort): build a reverse map target -> [sources] and
    walk it from node_id with a stack or BFS, collecting everything you reach.
    Don't include node_id itself.
    """
    node_ids = {node["id"] for node in graph.get("nodes", [])}
    reverse_map = {nid: [] for nid in node_ids}

    for edge in graph.get("edges", []):
        source = edge["source"]
        target = edge["target"]
        if target not in reverse_map or source not in node_ids:
            raise ValueError(f"edge {source}->{target} points at an unknown node")
        reverse_map[target].append(source)

    visited = set()
    stack = list(reverse_map.get(node_id, []))

    while stack:
        current = stack.pop()
        if current not in visited:
            visited.add(current)
            for upstream_node in reverse_map.get(current, []):
                if upstream_node not in visited:
                    stack.append(upstream_node)

    visited.discard(node_id)
    return visited
