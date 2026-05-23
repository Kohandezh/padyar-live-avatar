"""Tests for adapter factory and runtime config selection."""

from __future__ import annotations

import os

import pytest
from pydantic import SecretStr

from padyar_live.adapters.engine import FakeEngineAdapter
from padyar_live.adapters.factory import create_engine_adapter
from padyar_live.adapters.remote_engine import RemoteEngineAdapter
from padyar_live.api.app import create_app
from padyar_live.runtime.config import RuntimeConfig

# --- Factory tests ---


def test_fake_config_returns_fake_adapter() -> None:
    config = RuntimeConfig(engine_adapter="fake")
    adapter = create_engine_adapter(config)
    assert isinstance(adapter, FakeEngineAdapter)


def test_remote_config_returns_remote_adapter() -> None:
    config = RuntimeConfig(
        engine_adapter="remote",
        engine_url="http://engine.test:9000",
    )
    adapter = create_engine_adapter(config)
    assert isinstance(adapter, RemoteEngineAdapter)


def test_remote_config_passes_base_url_timeout_api_key() -> None:
    config = RuntimeConfig(
        engine_adapter="remote",
        engine_url="http://engine.test:9000",
        engine_timeout_seconds=10.0,
        engine_api_key=SecretStr("secret-123"),
    )
    adapter = create_engine_adapter(config)
    assert isinstance(adapter, RemoteEngineAdapter)
    assert adapter._config.base_url == "http://engine.test:9000"
    assert adapter._config.timeout_seconds == 10.0
    assert adapter._config.api_key == "secret-123"


def test_invalid_engine_adapter_raises_value_error() -> None:
    config = RuntimeConfig(engine_adapter="fake")
    config.engine_adapter = "invalid"
    with pytest.raises(ValueError, match="Invalid engine_adapter"):
        create_engine_adapter(config)


def test_remote_with_empty_url_raises_value_error() -> None:
    config = RuntimeConfig(engine_adapter="remote", engine_url="")
    config.engine_url = ""
    with pytest.raises(ValueError, match="engine_url must not be empty"):
        create_engine_adapter(config)


# --- App integration tests ---


def test_create_app_uses_factory_when_engine_is_none() -> None:
    config = RuntimeConfig(engine_adapter="fake")
    app = create_app(config=config, engine=None)
    assert app is not None


def test_create_app_explicit_engine_overrides_factory() -> None:
    config = RuntimeConfig(engine_adapter="remote", engine_url="http://should-not-be-used")
    explicit_engine = FakeEngineAdapter()
    app = create_app(config=config, engine=explicit_engine)
    assert app is not None


# --- Config validation tests ---


def test_config_default_is_fake() -> None:
    config = RuntimeConfig()
    assert config.engine_adapter == "fake"


def test_config_rejects_invalid_adapter() -> None:
    with pytest.raises(Exception):
        RuntimeConfig(engine_adapter="grpc")


# --- API key not exposed in repr ---


def test_api_key_not_in_repr() -> None:
    config = RuntimeConfig(
        engine_adapter="remote",
        engine_url="http://engine.test",
        engine_api_key=SecretStr("super-secret-key"),
    )
    repr_str = repr(config)
    assert "super-secret-key" not in repr_str


# --- Default engine_url ---


def test_default_engine_url() -> None:
    config = RuntimeConfig()
    assert config.engine_url == "http://localhost:9000"


def test_default_engine_api_key_is_none() -> None:
    config = RuntimeConfig()
    assert config.engine_api_key is None


# --- from_env tests ---


def test_from_env_selects_remote_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PADYAR_ENGINE_ADAPTER", "remote")
    monkeypatch.setenv("PADYAR_ENGINE_URL", "http://engine.test:9000")
    config = RuntimeConfig.from_env()
    assert config.engine_adapter == "remote"
    assert config.engine_url == "http://engine.test:9000"


def test_from_env_selects_fake_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PADYAR_ENGINE_ADAPTER", "fake")
    config = RuntimeConfig.from_env()
    assert config.engine_adapter == "fake"


def test_from_env_timeout_parses_float(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PADYAR_ENGINE_TIMEOUT_SECONDS", "7.5")
    config = RuntimeConfig.from_env()
    assert config.engine_timeout_seconds == 7.5


def test_from_env_api_key_masked_and_not_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PADYAR_ENGINE_ADAPTER", "remote")
    monkeypatch.setenv("PADYAR_ENGINE_URL", "http://engine.test")
    monkeypatch.setenv("PADYAR_ENGINE_API_KEY", "secret-env-key")
    config = RuntimeConfig.from_env()
    assert config.engine_api_key is not None
    assert config.engine_api_key.get_secret_value() == "secret-env-key"
    assert "secret-env-key" not in repr(config)


def test_from_env_without_vars_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure no PADYAR_ env vars are set
    for key in list(os.environ):
        if key.startswith("PADYAR_"):
            monkeypatch.delenv(key, raising=False)
    config = RuntimeConfig.from_env()
    assert config.engine_adapter == "fake"
    assert config.engine_url == "http://localhost:9000"
    assert config.engine_api_key is None


def test_from_env_overrides_with_explicit_kwargs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PADYAR_ENGINE_ADAPTER", "fake")
    config = RuntimeConfig.from_env(engine_adapter="remote", engine_url="http://override.test")
    assert config.engine_adapter == "remote"
    assert config.engine_url == "http://override.test"
