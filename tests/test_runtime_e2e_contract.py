"""Runtime E2E Contract Harness.

Verifies the full runtime path:
  RuntimeConfig.from_env() → create_engine_adapter() → RemoteEngineAdapter
  → Mock Engine Service → frame response → scheduler/fallback behavior.

No real network calls. No ML inference. In-process only.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from httpx import ASGITransport

from padyar_live.adapters.engine import EngineAdapter
from padyar_live.adapters.factory import create_engine_adapter
from padyar_live.adapters.remote_engine import (
    RemoteEngineAdapter,
    RemoteEngineConfig,
    RemoteEngineError,
)
from padyar_live.devtools.mock_engine import create_mock_engine_app
from padyar_live.runtime.config import RuntimeConfig
from padyar_live.scheduler.frame_scheduler import FrameScheduler

_URLOPENDOT = "padyar_live.adapters.remote_engine.urllib.request.urlopen"

# ---------------------------------------------------------------------------
# Helper: route RemoteEngineAdapter HTTP calls through an in-process ASGI app.
#
# We patch urllib.request.urlopen at the adapter module level (not the
# static method _urlopen) to avoid the bound-method / staticmethod
# descriptor conflict that patch.object causes.
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Mimics the urllib response object (context manager + read())."""

    def __init__(self, content: bytes) -> None:
        self._content = content

    def read(self) -> bytes:
        return self._content

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        pass


class _ASGIBridge:
    """Routes urllib calls to an in-process ASGI app via httpx AsyncClient."""

    def __init__(self, asgi_app: Any) -> None:
        self._app = asgi_app
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                transport=ASGITransport(app=self._app),
                base_url="http://mockengine",
            )
        return self._client

    def urlopen(self, request: Any, timeout: float = 5.0) -> _FakeResponse:
        # Called from asyncio.to_thread — we're in a worker thread with no event loop.
        content = asyncio.run(self._async_call(request))
        return _FakeResponse(content)

    async def _async_call(self, request: Any) -> bytes:
        client = self._get_client()
        method = request.get_method()
        url: str = request.full_url
        path = url.replace("http://mockengine", "")
        headers = dict(request.header_items()) if hasattr(request, "header_items") else {}
        body: bytes = request.data

        if method == "GET":
            resp = await client.get(path, headers=headers)
        else:
            resp = await client.post(path, content=body, headers=headers)
        return resp.content


@pytest.fixture
def mock_app() -> Any:
    return create_mock_engine_app()


@pytest.fixture
def bridge(mock_app: Any) -> _ASGIBridge:
    return _ASGIBridge(mock_app)


@pytest.fixture
def remote_adapter() -> RemoteEngineAdapter:
    config = RemoteEngineConfig(
        base_url="http://mockengine",
        timeout_seconds=5.0,
    )
    return RemoteEngineAdapter(config)


def _patch_urlopen(bridge: _ASGIBridge) -> Any:
    """Patch urllib.request.urlopen in the adapter module to use the bridge."""
    return patch(_URLOPENDOT, bridge.urlopen)


# ===================================================================
# Section 1: RuntimeConfig.from_env() → adapter selection
# ===================================================================


class TestConfigSelection:
    """RuntimeConfig.from_env() selects the correct adapter type."""

    def test_env_selects_remote(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PADYAR_ENGINE_ADAPTER", "remote")
        monkeypatch.setenv("PADYAR_ENGINE_URL", "http://mockengine")
        config = RuntimeConfig.from_env()
        assert config.engine_adapter == "remote"
        assert config.engine_url == "http://mockengine"

    def test_env_selects_fake(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PADYAR_ENGINE_ADAPTER", "fake")
        config = RuntimeConfig.from_env()
        assert config.engine_adapter == "fake"

    def test_env_defaults_to_fake(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in list(os.environ):
            if key.startswith("PADYAR_"):
                monkeypatch.delenv(key, raising=False)
        config = RuntimeConfig.from_env()
        assert config.engine_adapter == "fake"

    def test_env_timeout_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PADYAR_ENGINE_TIMEOUT_SECONDS", "3.0")
        config = RuntimeConfig.from_env()
        assert config.engine_timeout_seconds == 3.0


# ===================================================================
# Section 2: Factory → RemoteEngineAdapter creation
# ===================================================================


class TestFactoryCreatesRemote:
    """create_engine_adapter() produces RemoteEngineAdapter from config."""

    def test_factory_returns_remote_instance(self) -> None:
        config = RuntimeConfig(
            engine_adapter="remote",
            engine_url="http://mockengine",
        )
        adapter = create_engine_adapter(config)
        assert isinstance(adapter, RemoteEngineAdapter)

    def test_factory_remote_is_engine_adapter_subclass(self) -> None:
        config = RuntimeConfig(
            engine_adapter="remote",
            engine_url="http://mockengine",
        )
        adapter = create_engine_adapter(config)
        assert isinstance(adapter, EngineAdapter)

    def test_factory_passes_config_correctly(self) -> None:
        config = RuntimeConfig(
            engine_adapter="remote",
            engine_url="http://mockengine",
            engine_timeout_seconds=8.0,
        )
        adapter = create_engine_adapter(config)
        assert adapter._config.base_url == "http://mockengine"
        assert adapter._config.timeout_seconds == 8.0


# ===================================================================
# Section 3: RemoteEngineAdapter ↔ Mock Engine contract
# ===================================================================


class TestAdapterMockContract:
    """RemoteEngineAdapter request/response matches Mock Engine Service protocol."""

    @pytest.mark.asyncio
    async def test_generate_frames_returns_correct_count(
        self, remote_adapter: RemoteEngineAdapter, bridge: _ASGIBridge,
    ) -> None:
        with _patch_urlopen(bridge):
            frames = await remote_adapter.generate_frames("sess-1", b"\x00\x01", 4)
        assert len(frames) == 4

    @pytest.mark.asyncio
    async def test_frames_are_bytes(
        self, remote_adapter: RemoteEngineAdapter, bridge: _ASGIBridge,
    ) -> None:
        with _patch_urlopen(bridge):
            frames = await remote_adapter.generate_frames("sess-1", b"\x00", 2)
        for frame in frames:
            assert isinstance(frame, bytes)
            assert len(frame) > 0

    @pytest.mark.asyncio
    async def test_frames_have_jpeg_header(
        self, remote_adapter: RemoteEngineAdapter, bridge: _ASGIBridge,
    ) -> None:
        with _patch_urlopen(bridge):
            frames = await remote_adapter.generate_frames("sess-1", b"\x00", 3)
        for frame in frames:
            assert frame[:2] == b"\xff\xd8"

    @pytest.mark.asyncio
    async def test_frame_count_matches_request(
        self, remote_adapter: RemoteEngineAdapter, bridge: _ASGIBridge,
    ) -> None:
        with _patch_urlopen(bridge):
            frames = await remote_adapter.generate_frames("sess-1", b"\x00", 8)
        assert len(frames) == 8

    @pytest.mark.asyncio
    async def test_health_check_succeeds(
        self, remote_adapter: RemoteEngineAdapter, bridge: _ASGIBridge,
    ) -> None:
        with _patch_urlopen(bridge):
            result = await remote_adapter.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_request_payload_format(
        self, remote_adapter: RemoteEngineAdapter, bridge: _ASGIBridge,
    ) -> None:
        """Verify adapter sends the correct JSON fields."""
        audio = b"\x10\x20\x30\x40"
        captured_body: dict[str, Any] = {}

        original_urlopen = bridge.urlopen

        def capturing_urlopen(request: Any, timeout: float = 5.0) -> _FakeResponse:
            captured_body.update(json.loads(request.data))
            return original_urlopen(request, timeout)

        with patch(_URLOPENDOT, capturing_urlopen):
            await remote_adapter.generate_frames("sess-payload", audio, 3)

        assert captured_body["session_id"] == "sess-payload"
        assert captured_body["audio_chunk_b64"] == base64.b64encode(audio).decode("ascii")
        assert captured_body["frame_count"] == 3
        assert captured_body["format"] == "pcm_s16le_16000_mono"


# ===================================================================
# Section 4: Mock Engine Service contract details
# ===================================================================


class TestMockEngineContract:
    """Verify the Mock Engine Service returns what the adapter expects."""

    @pytest.mark.asyncio
    async def test_response_contains_required_fields(self, mock_app: Any) -> None:
        transport = ASGITransport(app=mock_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/generate_frames",
                json={
                    "session_id": "test",
                    "audio_chunk_b64": base64.b64encode(b"\x00").decode(),
                    "frame_count": 5,
                    "format": "pcm_s16le_16000_mono",
                },
            )
        data = resp.json()
        assert "frames_b64" in data
        assert "frame_count" in data
        assert data["frame_count"] == 5
        assert len(data["frames_b64"]) == 5

    @pytest.mark.asyncio
    async def test_frames_are_valid_base64_jpeg(self, mock_app: Any) -> None:
        transport = ASGITransport(app=mock_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/generate_frames",
                json={
                    "session_id": "test",
                    "audio_chunk_b64": base64.b64encode(b"\x00").decode(),
                    "frame_count": 3,
                    "format": "pcm_s16le_16000_mono",
                },
            )
        for frame_b64 in resp.json()["frames_b64"]:
            decoded = base64.b64decode(frame_b64)
            assert decoded[:2] == b"\xff\xd8"

    @pytest.mark.asyncio
    async def test_deterministic_output(self, mock_app: Any) -> None:
        transport = ASGITransport(app=mock_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "session_id": "det",
                "audio_chunk_b64": base64.b64encode(b"\x00").decode(),
                "frame_count": 2,
                "format": "pcm_s16le_16000_mono",
            }
            r1 = await client.post("/generate_frames", json=payload)
            r2 = await client.post("/generate_frames", json=payload)
        assert r1.json()["frames_b64"] == r2.json()["frames_b64"]


# ===================================================================
# Section 5: Failure handling — adapter errors
# ===================================================================


class TestAdapterFailureHandling:
    """Engine failure produces controlled adapter errors."""

    @pytest.mark.asyncio
    async def test_connection_refused_raises_remote_engine_error(self) -> None:
        config = RemoteEngineConfig(base_url="http://unreachable:9999", timeout_seconds=1.0)
        adapter = RemoteEngineAdapter(config)
        with pytest.raises(RemoteEngineError, match="request failed"):
            await adapter.generate_frames("sess-fail", b"\x00", 1)

    @pytest.mark.asyncio
    async def test_invalid_json_response_raises_error(self) -> None:
        config = RemoteEngineConfig(base_url="http://mockengine")
        adapter = RemoteEngineAdapter(config)

        def bad_json_urlopen(request: Any, timeout: float = 5.0) -> _FakeResponse:
            return _FakeResponse(b"not valid json")

        with patch(_URLOPENDOT, bad_json_urlopen):
            with pytest.raises(RemoteEngineError, match="invalid JSON"):
                await adapter.generate_frames("sess-bad", b"\x00", 1)

    @pytest.mark.asyncio
    async def test_frame_count_mismatch_raises_error(self) -> None:
        config = RemoteEngineConfig(base_url="http://mockengine")
        adapter = RemoteEngineAdapter(config)

        def mismatch_urlopen(request: Any, timeout: float = 5.0) -> _FakeResponse:
            frames = [base64.b64encode(b"\xff\xd8FAKE").decode("ascii")]
            return _FakeResponse(json.dumps(
                {"frames_b64": frames, "frame_count": 1, "source": "mock"}
            ).encode())

        with patch(_URLOPENDOT, mismatch_urlopen):
            with pytest.raises(RemoteEngineError, match="Frame count mismatch"):
                await adapter.generate_frames("sess-mismatch", b"\x00", 5)

    @pytest.mark.asyncio
    async def test_mock_engine_500_triggers_adapter_error(self) -> None:
        """FastAPI re-raises RuntimeError through ASGI transport in debug mode.
        The scheduler's fallback catches this — tested at scheduler level."""
        failing_app = create_mock_engine_app(fail_rate=1.0)
        failing_bridge = _ASGIBridge(failing_app)
        config = RemoteEngineConfig(base_url="http://mockengine")
        adapter = RemoteEngineAdapter(config)

        scheduler = FrameScheduler(
            engine=adapter,
            engine_timeout=5.0,
            fallback_enabled=True,
        )

        with patch(_URLOPENDOT, failing_bridge.urlopen):
            await scheduler.submit_audio("sess-500", b"\x00\x01\x02")

        frames = scheduler.get_next_frames_nowait()
        assert frames is not None
        assert all(f == b"" for f in frames)

    @pytest.mark.asyncio
    async def test_health_check_false_on_unreachable(self) -> None:
        config = RemoteEngineConfig(base_url="http://unreachable:9999", timeout_seconds=1.0)
        adapter = RemoteEngineAdapter(config)
        result = await adapter.health_check()
        assert result is False


# ===================================================================
# Section 6: Scheduler fallback with RemoteEngineAdapter
# ===================================================================


class TestSchedulerFallback:
    """Scheduler fallback handles adapter failures gracefully."""

    @pytest.mark.asyncio
    async def test_fallback_on_adapter_error(
        self, remote_adapter: RemoteEngineAdapter,
    ) -> None:
        scheduler = FrameScheduler(
            engine=remote_adapter,
            engine_timeout=5.0,
            fallback_enabled=True,
        )

        def failing_urlopen(request: Any, timeout: float = 5.0) -> _FakeResponse:
            raise RuntimeError("Engine crashed")

        with patch(_URLOPENDOT, failing_urlopen):
            await scheduler.submit_audio("sess-fallback", b"\x00\x01\x02")

        frames = scheduler.get_next_frames_nowait()
        assert frames is not None
        assert len(frames) > 0
        assert all(f == b"" for f in frames)

    @pytest.mark.asyncio
    async def test_fallback_on_engine_timeout(
        self, remote_adapter: RemoteEngineAdapter,
    ) -> None:
        scheduler = FrameScheduler(
            engine=remote_adapter,
            engine_timeout=0.1,
            fallback_enabled=True,
        )

        def slow_urlopen(request: Any, timeout: float = 5.0) -> _FakeResponse:
            import time
            time.sleep(10)
            return _FakeResponse(b"{}")

        with patch(_URLOPENDOT, slow_urlopen):
            await scheduler.submit_audio("sess-timeout", b"\x00\x01\x02")

        frames = scheduler.get_next_frames_nowait()
        assert frames is not None
        assert all(f == b"" for f in frames)

    @pytest.mark.asyncio
    async def test_fallback_disabled_raises_on_error(
        self, remote_adapter: RemoteEngineAdapter,
    ) -> None:
        scheduler = FrameScheduler(
            engine=remote_adapter,
            engine_timeout=5.0,
            fallback_enabled=False,
        )

        def failing_urlopen(request: Any, timeout: float = 5.0) -> _FakeResponse:
            raise RuntimeError("Engine crashed")

        with patch(_URLOPENDOT, failing_urlopen):
            with pytest.raises(RuntimeError, match="fallback is disabled"):
                await scheduler.submit_audio("sess-no-fallback", b"\x00")

    @pytest.mark.asyncio
    async def test_successful_flow_no_fallback(
        self, remote_adapter: RemoteEngineAdapter, bridge: _ASGIBridge,
    ) -> None:
        scheduler = FrameScheduler(
            engine=remote_adapter,
            engine_timeout=5.0,
            fallback_enabled=True,
        )

        with _patch_urlopen(bridge):
            await scheduler.submit_audio("sess-ok", b"\x00\x01\x02\x03")

        frames = scheduler.get_next_frames_nowait()
        assert frames is not None
        assert len(frames) == 4
        assert all(len(f) > 0 for f in frames)
        assert all(f[:2] == b"\xff\xd8" for f in frames)

    @pytest.mark.asyncio
    async def test_scheduler_tracks_latency_on_success(
        self, remote_adapter: RemoteEngineAdapter, bridge: _ASGIBridge,
    ) -> None:
        scheduler = FrameScheduler(
            engine=remote_adapter,
            engine_timeout=5.0,
            fallback_enabled=True,
        )

        with _patch_urlopen(bridge):
            await scheduler.submit_audio("sess-latency", b"\x00\x01\x02\x03")

        tracker = scheduler.latency
        assert tracker.total_frames >= 4


# ===================================================================
# Section 7: Runtime remains ML-free
# ===================================================================


class TestRuntimeMLFree:
    """Verify no ML imports are used in the E2E path."""

    def test_remote_adapter_module_has_no_ml_imports(self) -> None:
        import importlib

        mod = importlib.import_module("padyar_live.adapters.remote_engine")
        source = getattr(mod, "__file__", "")
        if source:
            with open(source) as f:
                code = f.read()
            forbidden = [
                "torch", "tensorflow", "onnxruntime",
                "diffusers", "transformers", "whisper",
                "mediapipe", "ultralytics", "cuda",
            ]
            for lib in forbidden:
                assert lib not in code.lower(), f"Forbidden ML import found: {lib}"

    def test_scheduler_module_has_no_ml_imports(self) -> None:
        import importlib

        mod = importlib.import_module("padyar_live.scheduler.frame_scheduler")
        source = getattr(mod, "__file__", "")
        if source:
            with open(source) as f:
                code = f.read()
            forbidden = [
                "torch", "tensorflow", "onnxruntime",
                "diffusers", "transformers", "whisper",
                "mediapipe", "ultralytics", "cuda",
            ]
            for lib in forbidden:
                assert lib not in code.lower(), f"Forbidden ML import found: {lib}"

    def test_factory_module_has_no_ml_imports(self) -> None:
        import importlib

        mod = importlib.import_module("padyar_live.adapters.factory")
        source = getattr(mod, "__file__", "")
        if source:
            with open(source) as f:
                code = f.read()
            forbidden = [
                "torch", "tensorflow", "onnxruntime",
                "diffusers", "transformers", "whisper",
                "mediapipe", "ultralytics", "cuda",
            ]
            for lib in forbidden:
                assert lib not in code.lower(), f"Forbidden ML import found: {lib}"


# ===================================================================
# Section 8: Full E2E — config → factory → adapter → mock → scheduler
# ===================================================================


class TestFullE2EPath:
    """Complete path from env config to scheduler output."""

    @pytest.mark.asyncio
    async def test_full_path_env_to_scheduler_output(
        self, bridge: _ASGIBridge, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PADYAR_ENGINE_ADAPTER", "remote")
        monkeypatch.setenv("PADYAR_ENGINE_URL", "http://mockengine")

        config = RuntimeConfig.from_env()
        assert config.engine_adapter == "remote"

        adapter = create_engine_adapter(config)
        assert isinstance(adapter, RemoteEngineAdapter)

        scheduler = FrameScheduler(
            engine=adapter,
            chunk_size=config.chunk_size,
            queue_max_size=config.queue_max_size,
            engine_timeout=config.engine_timeout_seconds,
            fallback_enabled=config.fallback_enabled,
        )

        with _patch_urlopen(bridge):
            await scheduler.submit_audio("e2e-session", b"\x00\x01\x02\x03")

        frames = scheduler.get_next_frames_nowait()
        assert frames is not None
        assert len(frames) == config.chunk_size
        assert all(isinstance(f, bytes) for f in frames)
        assert all(f[:2] == b"\xff\xd8" for f in frames)

    @pytest.mark.asyncio
    async def test_full_path_with_api_key(
        self, bridge: _ASGIBridge, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PADYAR_ENGINE_ADAPTER", "remote")
        monkeypatch.setenv("PADYAR_ENGINE_URL", "http://mockengine")
        monkeypatch.setenv("PADYAR_ENGINE_API_KEY", "test-api-key")

        config = RuntimeConfig.from_env()
        adapter = create_engine_adapter(config)
        assert isinstance(adapter, RemoteEngineAdapter)
        assert adapter._config.api_key == "test-api-key"

        scheduler = FrameScheduler(
            engine=adapter,
            fallback_enabled=True,
        )

        with _patch_urlopen(bridge):
            await scheduler.submit_audio("e2e-auth-session", b"\x00\x01")

        frames = scheduler.get_next_frames_nowait()
        assert frames is not None
        assert all(len(f) > 0 for f in frames)

    @pytest.mark.asyncio
    async def test_full_path_fallback_recovery(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PADYAR_ENGINE_ADAPTER", "remote")
        monkeypatch.setenv("PADYAR_ENGINE_URL", "http://mockengine")

        config = RuntimeConfig.from_env()
        adapter = create_engine_adapter(config)

        scheduler = FrameScheduler(
            engine=adapter,
            fallback_enabled=True,
            engine_timeout=0.1,
        )

        def failing_urlopen(request: Any, timeout: float = 5.0) -> _FakeResponse:
            raise RuntimeError("Engine unavailable")

        with patch(_URLOPENDOT, failing_urlopen):
            await scheduler.submit_audio("e2e-recovery", b"\x00\x01")

        frames_fail = scheduler.get_next_frames_nowait()
        assert frames_fail is not None
        assert all(f == b"" for f in frames_fail)

    @pytest.mark.asyncio
    async def test_full_path_multiple_chunks(
        self, bridge: _ASGIBridge, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PADYAR_ENGINE_ADAPTER", "remote")
        monkeypatch.setenv("PADYAR_ENGINE_URL", "http://mockengine")

        config = RuntimeConfig.from_env()
        adapter = create_engine_adapter(config)

        scheduler = FrameScheduler(
            engine=adapter,
            fallback_enabled=True,
        )

        with _patch_urlopen(bridge):
            await scheduler.submit_audio("e2e-multi", b"\x00\x01\x02\x03")
            await scheduler.submit_audio("e2e-multi", b"\x04\x05\x06\x07")
            await scheduler.submit_audio("e2e-multi", b"\x08\x09\x0a\x0b")

        batch1 = scheduler.get_next_frames_nowait()
        batch2 = scheduler.get_next_frames_nowait()
        batch3 = scheduler.get_next_frames_nowait()

        for batch in [batch1, batch2, batch3]:
            assert batch is not None
            assert len(batch) == config.chunk_size
            assert all(f[:2] == b"\xff\xd8" for f in batch)
