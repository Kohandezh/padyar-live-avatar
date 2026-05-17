import pytest

from padyar_live.adapters.engine import FakeEngineAdapter
from padyar_live.api.app import create_app
from padyar_live.runtime.config import RuntimeConfig


@pytest.fixture
def config():
    return RuntimeConfig()


@pytest.fixture
def engine():
    return FakeEngineAdapter()


@pytest.fixture
def app(config, engine):
    return create_app(config, engine)


@pytest.fixture
def client(app):
    from httpx import ASGITransport, AsyncClient
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
