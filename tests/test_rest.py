import pytest
from httpx import ASGITransport, AsyncClient

from padyar_live.adapters.engine import FakeEngineAdapter
from padyar_live.api.app import create_app
from padyar_live.runtime.config import RuntimeConfig


@pytest.fixture
def client():
    app = create_app(RuntimeConfig(), FakeEngineAdapter())
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_health(client):
    async with client as c:
        resp = await c.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert data["uptime_seconds"] >= 0


@pytest.mark.asyncio
async def test_create_session(client):
    async with client as c:
        resp = await c.post("/session", json={"avatar_id": "test", "language": "persian"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["status"] == "active"
    assert "/ws/live" in data["ws_url"]


@pytest.mark.asyncio
async def test_list_sessions(client):
    async with client as c:
        await c.post("/session", json={"avatar_id": "a1"})
        await c.post("/session", json={"avatar_id": "a2"})
        resp = await c.get("/session")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["sessions"]) == 2


@pytest.mark.asyncio
async def test_get_session(client):
    async with client as c:
        create = await c.post("/session", json={})
        session_id = create.json()["session_id"]
        resp = await c.get(f"/session/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == session_id


@pytest.mark.asyncio
async def test_get_session_not_found(client):
    async with client as c:
        resp = await c.get("/session/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_close_session(client):
    async with client as c:
        create = await c.post("/session", json={})
        session_id = create.json()["session_id"]
        resp = await c.delete(f"/session/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_close_session_not_found(client):
    async with client as c:
        resp = await c.delete("/session/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    async with client as c:
        resp = await c.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_frames" in data
    assert "avg_latency_ms" in data
    assert "p95_latency_ms" in data
    assert "active_sessions" in data
    assert "active_connections" in data
    assert "fallback_count" in data
    assert "fallback_rate" in data
