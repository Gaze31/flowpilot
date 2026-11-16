"""The API Key: writes need it once it is set, reads never do."""

from app.core.config import get_settings

GRAPH = {"nodes": [{"id": "n1", "type": "trigger.manual", "config": {}}], "edges": []}
NEW_WORKFLOW = {"name": "t", "graph": GRAPH}


async def test_no_key_configured_means_open(client):
    resp = await client.post("/workflows", json=NEW_WORKFLOW)
    assert resp.status_code == 201


async def test_write_without_key_is_rejected(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "api_key", "secret")
    resp = await client.post("/workflows", json=NEW_WORKFLOW)
    assert resp.status_code == 401


async def test_wrong_key_is_rejected(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "api_key", "secret")
    resp = await client.post("/workflows", json=NEW_WORKFLOW, headers={"X-API-Key": "guess"})
    assert resp.status_code == 401


async def test_right_key_can_create_and_run(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "api_key", "secret")
    key = {"X-API-Key": "secret"}
    created = await client.post("/workflows", json=NEW_WORKFLOW, headers=key)
    assert created.status_code == 201
    workflow_id = created.json()["id"]

    assert (await client.post(f"/workflows/{workflow_id}/runs")).status_code == 401
    assert (await client.post(f"/workflows/{workflow_id}/runs", headers=key)).status_code == 202


async def test_reads_stay_public(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "api_key", "secret")
    resp = await client.get("/workflows")
    assert resp.status_code == 200
