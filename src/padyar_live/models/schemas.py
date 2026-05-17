from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SessionStatus(StrEnum):
    ACTIVE = "active"
    IDLE = "idle"
    CLOSED = "closed"
    ERROR = "error"


class SessionConfig(BaseModel):
    avatar_id: str = "default"
    fps: int = Field(default=25, ge=1, le=60)
    language: str = "persian"
    engine_url: str = "http://localhost:7860"


class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: SessionStatus = SessionStatus.ACTIVE
    config: SessionConfig = Field(default_factory=SessionConfig)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_active_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SessionCreateRequest(BaseModel):
    avatar_id: str = "default"
    fps: int = 25
    language: str = "persian"
    engine_url: str = "http://localhost:7860"


class SessionCreateResponse(BaseModel):
    session_id: str
    status: SessionStatus
    ws_url: str


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    uptime_seconds: float = 0.0


class MetricsResponse(BaseModel):
    total_frames: int
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    fallback_count: int
    fallback_rate: float
    within_target: bool
    active_sessions: int
    active_connections: int


class WSMessage(BaseModel):
    """Protocol message for WebSocket communication."""
    type: str  # "audio", "text", "control", "frame_request"
    session_id: str
    payload: dict[str, object] = Field(default_factory=dict)
    timestamp: float = Field(default=0.0)


class FrameResult(BaseModel):
    """A single generated frame result."""
    frame_index: int
    session_id: str
    data: bytes
    latency_ms: float
    source: str = "engine"  # "engine" or "fallback"


class WSError(BaseModel):
    """Structured error sent over WebSocket."""
    code: str
    message: str
    session_id: str = ""
