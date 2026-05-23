from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field, SecretStr


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

    # Engine adapter selection
    engine_adapter: str = Field(default="fake", pattern=r"^(fake|remote)$")
    engine_url: str = "http://localhost:9000"
    engine_api_key: SecretStr | None = None

    @classmethod
    def from_env(cls, **overrides: Any) -> RuntimeConfig:
        """Create config from environment variables with PADYAR_ prefix."""
        env_map: dict[str, Any] = {}

        if v := os.getenv("PADYAR_ENGINE_ADAPTER"):
            env_map["engine_adapter"] = v
        if v := os.getenv("PADYAR_ENGINE_URL"):
            env_map["engine_url"] = v
        if v := os.getenv("PADYAR_ENGINE_API_KEY"):
            env_map["engine_api_key"] = SecretStr(v)
        if v := os.getenv("PADYAR_ENGINE_TIMEOUT_SECONDS"):
            env_map["engine_timeout_seconds"] = float(v)

        env_map.update(overrides)
        return cls(**env_map)
