"""Week 2: starting runs through the API, and the worker picking them up."""

from app import worker
from app.engine.queue import dequeue_run
from tests.conftest import chain_graph, raise_if_todo, todo

GRAPH = chain_graph(("n1", "trigger.manual", {}), ("n2", "test.echo", {"x": "{{n1.output.payload}}"}))


async def create(client, graph=GRAPH) -> str:
    return (await client.post("/workflows", json={"name": "t", "graph": graph})).json()["id"]


@todo(2, "start run: topological_sort + enqueue_run")
async def test_start_run_queues_it(client):
    wf_id = await create(client)
    r = await client.post(f"/workflows/{wf_id}/runs")
    raise_if_todo(r)
    assert r.status_code == 202
    run = r.json()
    assert run["status"] == "queued"
    assert str(await dequeue_run(timeout=1)) == run["id"]


async def test_cycle_is_rejected_before_queueing(client, fresh_db_and_redis):
    g = {
        "nodes": [{"id": "a", "type": "test.echo"}, {"id": "b", "type": "test.echo"}],
        "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}],
    }
    wf_id = await create(client, g)
    r = await client.post(f"/workflows/{wf_id}/runs")
    raise_if_todo(r)
    assert r.status_code == 422
    assert await fresh_db_and_redis.llen("flowpilot:runs") == 0  # nothing was queued


@todo(2, "worker.process_one")
async def test_worker_runs_a_queued_run_end_to_end(client):
    wf_id = await create(client)
    r = await client.post(f"/workflows/{wf_id}/runs")
    raise_if_todo(r)
    run_id = r.json()["id"]

    assert await worker.process_one(timeout=1) is True

    detail = (await client.get(f"/runs/{run_id}")).json()
    assert detail["status"] == "succeeded"
    assert [s["node_id"] for s in detail["steps"]] == ["n1", "n2"]
    assert (await client.get(f"/workflows/{wf_id}/runs")).json()[0]["id"] == run_id
