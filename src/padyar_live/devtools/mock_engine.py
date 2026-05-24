"""Mock engine service — implements the RemoteEngineAdapter HTTP protocol for local testing."""

from __future__ import annotations

import asyncio
import base64
import random

from fastapi import FastAPI
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    session_id: str
    audio_chunk_b64: str
    frame_count: int = Field(default=4, ge=1)
    format: str = "pcm_s16le_16000_mono"


class GenerateResponse(BaseModel):
    frames_b64: list[str]
    frame_count: int
    source: str = "mock_engine"


def _mock_jpeg(index: int) -> bytes:
    """Deterministic fake JPEG — minimal valid header + index byte."""
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xd9"
        + bytes([index & 0xFF])
    )


def create_mock_engine_app(
    latency_ms: float = 0.0,
    fail_rate: float = 0.0,
) -> FastAPI:
    """Create a FastAPI app that mimics the remote engine protocol.

    Args:
        latency_ms: Simulated processing delay per request.
        fail_rate: Probability (0.0-1.0) of returning a 500 error.
    """
    app = FastAPI(title="PadYar Mock Engine", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/generate_frames", response_model=GenerateResponse)
    async def generate_frames(req: GenerateRequest) -> GenerateResponse:
        if fail_rate > 0 and random.random() < fail_rate:
            raise RuntimeError("Simulated engine failure")

        if latency_ms > 0:
            await asyncio.sleep(latency_ms / 1000.0)

        frames = [
            base64.b64encode(_mock_jpeg(i)).decode("ascii")
            for i in range(req.frame_count)
        ]
        return GenerateResponse(
            frames_b64=frames,
            frame_count=req.frame_count,
        )

    return app
