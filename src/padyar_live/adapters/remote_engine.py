from __future__ import annotations

import asyncio
import base64
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from padyar_live.adapters.engine import EngineAdapter


class RemoteEngineError(Exception):
    """Error from the remote inference engine."""


@dataclass
class RemoteEngineConfig:
    """Configuration for the remote engine HTTP adapter."""

    base_url: str
    timeout_seconds: float = 5.0
    health_path: str = "/health"
    generate_path: str = "/generate_frames"
    api_key: str | None = None


class RemoteEngineAdapter(EngineAdapter):
    """Connects to an external inference engine over HTTP.

    This adapter is a thin HTTP client — no ML code lives here.
    All inference happens on the remote engine server.
    """

    def __init__(self, config: RemoteEngineConfig) -> None:
        self._config = config

    async def generate_frames(
        self,
        session_id: str,
        audio_chunk: bytes,
        frame_count: int,
    ) -> list[bytes]:
        payload = {
            "session_id": session_id,
            "audio_chunk_b64": base64.b64encode(audio_chunk).decode("ascii"),
            "frame_count": frame_count,
            "format": "pcm_s16le_16000_mono",
        }
        body = json.dumps(payload).encode("utf-8")

        url = self._config.base_url.rstrip("/") + self._config.generate_path
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        self._add_auth(request)

        try:
            response_data = await asyncio.to_thread(
                self._urlopen, request, self._config.timeout_seconds
            )
        except (urllib.error.URLError, OSError) as exc:
            raise RemoteEngineError(
                f"Remote engine request failed: {exc}"
            ) from exc

        try:
            result = json.loads(response_data)
        except (json.JSONDecodeError, ValueError) as exc:
            raise RemoteEngineError(
                f"Remote engine returned invalid JSON: {exc}"
            ) from exc

        returned_count = result.get("frame_count", 0)
        if returned_count != frame_count:
            raise RemoteEngineError(
                f"Frame count mismatch: requested {frame_count}, "
                f"got {returned_count}"
            )

        frames_b64: list[str] = result.get("frames_b64", [])
        try:
            return [base64.b64decode(f) for f in frames_b64]
        except Exception as exc:
            raise RemoteEngineError(
                f"Failed to decode frame data: {exc}"
            ) from exc

    async def health_check(self) -> bool:
        url = self._config.base_url.rstrip("/") + self._config.health_path
        request = urllib.request.Request(url, method="GET")
        self._add_auth(request)

        try:
            await asyncio.to_thread(
                self._urlopen, request, self._config.timeout_seconds
            )
            return True
        except (urllib.error.URLError, OSError):
            return False

    def _add_auth(self, request: urllib.request.Request) -> None:
        if self._config.api_key:
            request.add_header(
                "Authorization", f"Bearer {self._config.api_key}"
            )

    @staticmethod
    def _urlopen(
        request: urllib.request.Request, timeout: float
    ) -> bytes:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            data: bytes = resp.read()
            return data
