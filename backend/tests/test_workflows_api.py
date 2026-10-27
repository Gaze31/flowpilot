"""Workflow CRUD + graph shape validation. These pass from day one: read them as examples."""

from tests.conftest import chain_graph

GRAPH = chain_graph(("n1", "trigger.manual", {"payload": {"hi": 1}}), ("n2", "test.echo", {"x": 1}))


async def test_health(client):
    r = await client.get("/health")
    assert r.json() == {"status": "ok"}


async def test_create_get_list_update_delete(client):
    r = await client.post("/workflows", json={"name": "Morning digest", "graph": GRAPH})
    assert r.status_code == 201
    wf = r.json()
    assert wf["name"] == "Morning digest"
    assert [n["id"] for n in wf["graph"]["nodes"]] == ["n1", "n2"]

    assert (await client.get(f"/workflows/{wf['id']}")).json()["id"] == wf["id"]
    assert len((await client.get("/workflows")).json()) == 1

    r = await client.patch(f"/workflows/{wf['id']}", json={"name": "Renamed"})
    assert r.status_code == 200 and r.json()["name"] == "Renamed"

    assert (await client.delete(f"/workflows/{wf['id']}")).status_code == 204
    assert (await client.get(f"/workflows/{wf['id']}")).status_code == 404


async def test_unknown_workflow_is_404(client):
    r = await client.get("/workflows/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


async def test_rejects_duplicate_node_ids(client):
    g = {"nodes": [{"id": "a", "type": "test.echo"}, {"id": "a", "type": "test.echo"}], "edges": []}
    assert (await client.post("/workflows", json={"name": "x", "graph": g})).status_code == 422


async def test_rejects_unknown_node_type(client):
    g = {"nodes": [{"id": "a", "type": "does.not.exist"}], "edges": []}
    assert (await client.post("/workflows", json={"name": "x", "graph": g})).status_code == 422


async def test_rejects_edge_to_missing_node(client):
    g = {"nodes": [{"id": "a", "type": "test.echo"}], "edges": [{"source": "a", "target": "ghost"}]}
    assert (await client.post("/workflows", json={"name": "x", "graph": g})).status_code == 422


async def test_rejects_self_loop(client):
    g = {"nodes": [{"id": "a", "type": "test.echo"}], "edges": [{"source": "a", "target": "a"}]}
    assert (await client.post("/workflows", json={"name": "x", "graph": g})).status_code == 422
