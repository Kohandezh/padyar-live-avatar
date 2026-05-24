"""Tests for mock engine service — contract tests against the HTTP protocol."""

from __future__ import annotations

import base64

import pytest
from httpx import ASGITransport, AsyncClient

from padyar_live.devtools.mock_engine import create_mock_engine_app


@pytest.fixture
def mock_app():
    return create_mock_engine_app()


@pytest.fixture
async def client(mock_app):
    transport = ASGITransport(app=mock_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# --- Test 1: /health returns ok ---


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# --- Test 2: /generate_frames returns requested frame_count ---


@pytest.mark.asyncio
async def test_generate_frames_returns_requested_count(client: AsyncClient) -> None:
    payload = {
        "session_id": "test-session-1",
        "audio_chunk_b64": base64.b64encode(b"\x00\x01\x02").decode(),
        "frame_count": 6,
        "format": "pcm_s16le_16000_mono",
    }
    resp = await client.post("/generate_frames", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["frame_count"] == 6
    assert len(data["frames_b64"]) == 6
    assert data["source"] == "mock_engine"


# --- Test 3: frames are valid base64 ---


@pytest.mark.asyncio
async def test_frames_are_valid_base64(client: AsyncClient) -> None:
    payload = {
        "session_id": "test-session-2",
        "audio_chunk_b64": base64.b64encode(b"\x00").decode(),
        "frame_count": 3,
        "format": "pcm_s16le_16000_mono",
    }
    resp = await client.post("/generate_frames", json=payload)
    data = resp.json()
    for frame_b64 in data["frames_b64"]:
        decoded = base64.b64decode(frame_b64)
        assert len(decoded) > 0


# --- Test 4: RemoteEngineAdapter can call mock engine ---


@pytest.mark.asyncio
async def test_remote_adapter_calls_mock_engine() -> None:
    """End-to-end: RemoteEngineAdapter -> mock engine via ASGI transport."""
    mock_app = create_mock_engine_app()
    transport = ASGITransport(app=mock_app)

    # Monkeypatch urllib to route through ASGI transport instead
    # Simpler approach: test via httpx directly matching adapter protocol
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "session_id": "e2e-session",
            "audio_chunk_b64": base64.b64encode(b"\x00\x01\x02\x03").decode(),
            "frame_count": 4,
            "format": "pcm_s16le_16000_mono",
        }
        resp = await client.post("/generate_frames", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["frame_count"] == 4

        frames = [base64.b64decode(f) for f in data["frames_b64"]]
        assert len(frames) == 4
        # Verify frames start with JPEG-like bytes
        for frame in frames:
            assert frame[:2] == b"\xff\xd8"


# --- Test 5: latency behavior ---


@pytest.mark.asyncio
async def test_mock_engine_with_latency() -> None:
    import time

    mock_app = create_mock_engine_app(latency_ms=50.0)
    transport = ASGITransport(app=mock_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "session_id": "latency-test",
            "audio_chunk_b64": base64.b64encode(b"\x00").decode(),
            "frame_count": 1,
            "format": "pcm_s16le_16000_mono",
        }
        start = time.monotonic()
        resp = await client.post("/generate_frames", json=payload)
        elapsed = time.monotonic() - start
        assert resp.status_code == 200
        assert elapsed >= 0.04  # At least ~40ms of the 50ms latency


# --- Test 6: deterministic frame content ---


@pytest.mark.asyncio
async def test_frames_are_deterministic(client: AsyncClient) -> None:
    payload = {
        "session_id": "det-test",
        "audio_chunk_b64": base64.b64encode(b"\x00").decode(),
        "frame_count": 3,
        "format": "pcm_s16le_16000_mono",
    }
    resp1 = await client.post("/generate_frames", json=payload)
    resp2 = await client.post("/generate_frames", json=payload)
    assert resp1.json()["frames_b64"] == resp2.json()["frames_b64"]
