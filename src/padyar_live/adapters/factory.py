from __future__ import annotations

from padyar_live.adapters.engine import EngineAdapter, FakeEngineAdapter
from padyar_live.adapters.remote_engine import (
    RemoteEngineAdapter,
    RemoteEngineConfig,
)
from padyar_live.runtime.config import RuntimeConfig


def create_engine_adapter(config: RuntimeConfig) -> EngineAdapter:
    """Create the appropriate engine adapter based on runtime config."""

    if config.engine_adapter == "fake":
        return FakeEngineAdapter()

    if config.engine_adapter == "remote":
        if not config.engine_url:
            raise ValueError(
                "engine_url must not be empty when engine_adapter is 'remote'"
            )
        return RemoteEngineAdapter(
            RemoteEngineConfig(
                base_url=config.engine_url,
                timeout_seconds=config.engine_timeout_seconds,
                api_key=config.engine_api_key.get_secret_value()
                if config.engine_api_key
                else None,
            )
        )

    raise ValueError(
        f"Invalid engine_adapter: {config.engine_adapter!r}. "
        "Must be 'fake' or 'remote'."
    )
