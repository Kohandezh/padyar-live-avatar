from __future__ import annotations

from pydantic import BaseModel, Field


class RuntimeConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    fps: int = 25
    queue_max_size: int = Field(default=120, ge=10)
    chunk_size: int = Field(default=4, ge=1)
    engine_timeout_seconds: float = Field(default=5.0, ge=0.1)
    fallback_enabled: bool = True
    latency_target_ms: float = 120.0
    ws_ping_interval_seconds: float = Field(default=20.0, ge=1.0)
    ws_ping_timeout_seconds: float = Field(default=30.0, ge=5.0)
    max_message_size_bytes: int = Field(default=1024 * 1024, ge=1024)  # 1MB default
