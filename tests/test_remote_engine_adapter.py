"""Tests for RemoteEngineAdapter — no real network calls."""

from __future__ import annotations

import base64
import json
import urllib.error
from unittest.mock import patch

import pytest

from padyar_live.adapters.engine import EngineAdapter
from padyar_live.adapters.remote_engine import (
    RemoteEngineAdapter,
    RemoteEngineConfig,
    RemoteEngineError,
)


def _make_config(**overrides: object) -> RemoteEngineConfig:
    defaults = {"base_url": "http://engine.test"}
    defaults.update(overrides)
    return RemoteEngineConfig(**defaults)  # type: ignore[arg-type]


def _make_response(frames_b64: list[str], frame_count: int) -> bytes:
    return json.dumps(
        {"frames_b64": frames_b64, "frame_count": frame_count, "source": "remote_engine"}
    ).encode("utf-8")


FAKE_JPEG = b"\xff\xd8\xff\xe0FAKE"
FAKE_JPEG_B64 = base64.b64encode(FAKE_JPEG).decode("ascii")


# --- Test 1: request payload shape ---


@pytest.mark.asyncio
async def test_request_payload_shape() -> None:
    """Verify the HTTP request body contains correct fields."""
    config = _make_config()
    adapter = RemoteEngineAdapter(config)
    audio = b"\x00\x01\x02\x03"

    with patch("padyar_live.adapters.remote_engine.urllib.request.urlopen") as mock_urlopen:

        class FakeResponse:
            def read(self) -> bytes:
                return _make_response([FAKE_JPEG_B64, FAKE_JPEG_B64], 2)

            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *args: object) -> None:
                pass

        mock_urlopen.return_value = FakeResponse()
        await adapter.generate_frames("sess-1", audio, 2)

        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        body = json.loads(request_obj.data)

        assert body["session_id"] == "sess-1"
        assert body["audio_chunk_b64"] == base64.b64encode(audio).decode("ascii")
        assert body["frame_count"] == 2
        assert body["format"] == "pcm_s16le_16000_mono"


# --- Test 2: response frames decoded from base64 ---


@pytest.mark.asyncio
async def test_frames_decoded_from_base64() -> None:
    config = _make_config()
    adapter = RemoteEngineAdapter(config)

    with patch("padyar_live.adapters.remote_engine.urllib.request.urlopen") as mock_urlopen:

        class FakeResponse:
            def read(self) -> bytes:
                return _make_response([FAKE_JPEG_B64, FAKE_JPEG_B64], 2)

            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *args: object) -> None:
                pass

        mock_urlopen.return_value = FakeResponse()
        frames = await adapter.generate_frames("sess-1", b"\x00", 2)

        assert frames == [FAKE_JPEG, FAKE_JPEG]


# --- Test 3: wrong frame_count raises RemoteEngineError ---


@pytest.mark.asyncio
async def test_wrong_frame_count_raises() -> None:
    config = _make_config()
    adapter = RemoteEngineAdapter(config)

    with patch("padyar_live.adapters.remote_engine.urllib.request.urlopen") as mock_urlopen:

        class FakeResponse:
            def read(self) -> bytes:
                return _make_response([FAKE_JPEG_B64], 1)

            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *args: object) -> None:
                pass

        mock_urlopen.return_value = FakeResponse()

        with pytest.raises(RemoteEngineError, match="Frame count mismatch"):
            await adapter.generate_frames("sess-1", b"\x00", 3)


# --- Test 4: invalid JSON raises RemoteEngineError ---


@pytest.mark.asyncio
async def test_invalid_json_raises() -> None:
    config = _make_config()
    adapter = RemoteEngineAdapter(config)

    with patch("padyar_live.adapters.remote_engine.urllib.request.urlopen") as mock_urlopen:

        class FakeResponse:
            def read(self) -> bytes:
                return b"not json at all"

            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *args: object) -> None:
                pass

        mock_urlopen.return_value = FakeResponse()

        with pytest.raises(RemoteEngineError, match="invalid JSON"):
            await adapter.generate_frames("sess-1", b"\x00", 1)


# --- Test 5: timeout / urllib error raises RemoteEngineError ---


@pytest.mark.asyncio
async def test_urllib_error_raises() -> None:
    config = _make_config()
    adapter = RemoteEngineAdapter(config)

    with patch("padyar_live.adapters.remote_engine.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.URLError("timeout")

        with pytest.raises(RemoteEngineError, match="request failed"):
            await adapter.generate_frames("sess-1", b"\x00", 1)


# --- Test 6: health_check returns True when healthy ---


@pytest.mark.asyncio
async def test_health_check_true_when_healthy() -> None:
    config = _make_config()
    adapter = RemoteEngineAdapter(config)

    with patch("padyar_live.adapters.remote_engine.urllib.request.urlopen") as mock_urlopen:

        class FakeResponse:
            def read(self) -> bytes:
                return b'{"status":"ok"}'

            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *args: object) -> None:
                pass

        mock_urlopen.return_value = FakeResponse()
        result = await adapter.health_check()
        assert result is True


# --- Test 7: health_check returns False on failure ---


@pytest.mark.asyncio
async def test_health_check_false_on_failure() -> None:
    config = _make_config()
    adapter = RemoteEngineAdapter(config)

    with patch("padyar_live.adapters.remote_engine.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        result = await adapter.health_check()
        assert result is False


# --- Test 8: Authorization header added when api_key provided ---


@pytest.mark.asyncio
async def test_authorization_header_added() -> None:
    config = _make_config(api_key="secret-key-123")
    adapter = RemoteEngineAdapter(config)

    with patch("padyar_live.adapters.remote_engine.urllib.request.urlopen") as mock_urlopen:

        class FakeResponse:
            def read(self) -> bytes:
                return _make_response([FAKE_JPEG_B64], 1)

            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *args: object) -> None:
                pass

        mock_urlopen.return_value = FakeResponse()
        await adapter.generate_frames("sess-1", b"\x00", 1)

        request_obj = mock_urlopen.call_args[0][0]
        assert request_obj.get_header("Authorization") == "Bearer secret-key-123"


# --- Test 9: RemoteEngineAdapter is an EngineAdapter subclass ---


def test_remote_adapter_is_engine_adapter_subclass() -> None:
    assert issubclass(RemoteEngineAdapter, EngineAdapter)


# --- Test 10: no auth header when api_key is None ---


@pytest.mark.asyncio
async def test_no_auth_header_without_api_key() -> None:
    config = _make_config()
    adapter = RemoteEngineAdapter(config)

    with patch("padyar_live.adapters.remote_engine.urllib.request.urlopen") as mock_urlopen:

        class FakeResponse:
            def read(self) -> bytes:
                return _make_response([FAKE_JPEG_B64], 1)

            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *args: object) -> None:
                pass

        mock_urlopen.return_value = FakeResponse()
        await adapter.generate_frames("sess-1", b"\x00", 1)

        request_obj = mock_urlopen.call_args[0][0]
        assert request_obj.get_header("Authorization") is None
