"""Week 1: topological sort and upstream_of. Make these pass first."""

import pytest

from app.engine.graph import topological_sort, upstream_of
from app.errors import CycleError


def g(node_ids, edges):
    return {"nodes": [{"id": i, "type": "test.echo"} for i in node_ids], "edges": [{"source": a, "target": b} for a, b in edges]}


def test_single_node():
    assert topological_sort(g(["a"], [])) == ["a"]


def test_chain():
    assert topological_sort(g(["a", "b", "c"], [("a", "b"), ("b", "c")])) == ["a", "b", "c"]


def test_chain_listed_out_of_order():
    # the order of graph["nodes"] must not matter when edges decide it
    assert topological_sort(g(["c", "b", "a"], [("a", "b"), ("b", "c")])) == ["a", "b", "c"]


def test_diamond_is_deterministic():
    #   a -> b -> d
    #   a -> c -> d     ties are broken by the order nodes are listed
    assert topological_sort(g(["a", "b", "c", "d"], [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")])) == ["a", "b", "c", "d"]


def test_independent_nodes_keep_listed_order():
    assert topological_sort(g(["x", "y", "z"], [])) == ["x", "y", "z"]


def test_cycle_raises():
    with pytest.raises(CycleError) as e:
        topological_sort(g(["a", "b", "c"], [("a", "b"), ("b", "c"), ("c", "b")]))
    assert "b" in str(e.value) and "c" in str(e.value)


def test_upstream_of():
    graph = g(["a", "b", "c", "d"], [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")])
    assert upstream_of(graph, "d") == {"a", "b", "c"}
    assert upstream_of(graph, "b") == {"a"}
    assert upstream_of(graph, "a") == set()
