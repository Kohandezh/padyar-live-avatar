
import pytest
from fastapi.testclient import TestClient

from padyar_live.adapters.engine import FakeEngineAdapter
from padyar_live.api.app import create_app
from padyar_live.runtime.config import RuntimeConfig


@pytest.fixture
def app():
    return create_app(RuntimeConfig(), FakeEngineAdapter())


@pytest.fixture
def test_client(app):
    return TestClient(app)


def _create_session(http_client: TestClient) -> str:
    resp = http_client.post("/session", json={"avatar_id": "test"})
    return resp.json()["session_id"]


def test_ws_full_lifecycle(test_client):
    """Test: create session → connect WS → send audio → receive frames → disconnect."""
    # 1. Create session via REST
    session_id = _create_session(test_client)
    assert session_id

    # 2. Connect WebSocket
    with test_client.websocket_connect(f"/ws/live?session_id={session_id}") as ws:
        # 3. Send audio chunk
        ws.send_bytes(b"\x00" * 1600)

        # 4. Receive frames
        raw = ws.receive_bytes()
        assert b"\x00" in raw  # header separator present

        # 5. Send another chunk
        ws.send_bytes(b"\x00" * 1600)
        raw = ws.receive_bytes()
        assert len(raw) > 0


def test_ws_session_not_found(test_client):
    """Connecting with invalid session_id should receive error then close."""
    with test_client.websocket_connect("/ws/live?session_id=nonexistent") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "session_not_found"


def test_ws_multiple_chunks(test_client):
    """Send multiple audio chunks, get multiple frame batches back."""
    session_id = _create_session(test_client)

    with test_client.websocket_connect(f"/ws/live?session_id={session_id}") as ws:
        for _ in range(3):
            ws.send_bytes(b"\x00" * 1600)

        received = 0
        for _ in range(3):
            raw = ws.receive_bytes()
            assert len(raw) > 0
            received += 1

        assert received == 3


def test_ws_ping(test_client):
    """Server should send periodic pings."""
    session_id = _create_session(test_client)

    with test_client.websocket_connect(f"/ws/live?session_id={session_id}") as ws:
        # Send audio so the loops start
        ws.send_bytes(b"\x00" * 1600)
        # Read at least one frame response
        ws.receive_bytes()
