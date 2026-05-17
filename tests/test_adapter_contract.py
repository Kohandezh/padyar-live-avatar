from abc import ABC

import pytest

from padyar_live.adapters.engine import EngineAdapter, FakeEngineAdapter


def test_engine_adapter_is_abstract():
    """EngineAdapter cannot be instantiated directly."""
    assert issubclass(EngineAdapter, ABC)
    with pytest.raises(TypeError):
        EngineAdapter()


def test_fake_engine_implements_contract():
    """FakeEngineAdapter implements all abstract methods."""
    engine = FakeEngineAdapter()
    assert hasattr(engine, "generate_frames")
    assert hasattr(engine, "health_check")


@pytest.mark.asyncio
async def test_adapter_contract_generate_frames():
    """generate_frames must return list[bytes] with correct count."""
    engine = FakeEngineAdapter()
    result = await engine.generate_frames("test", b"\x00" * 1600, 8)
    assert isinstance(result, list)
    assert len(result) == 8
    for frame in result:
        assert isinstance(frame, bytes)


@pytest.mark.asyncio
async def test_adapter_contract_health_check():
    """health_check must return bool."""
    engine = FakeEngineAdapter()
    result = await engine.health_check()
    assert isinstance(result, bool)
    assert result is True


@pytest.mark.asyncio
async def test_adapter_contract_zero_frames():
    """generate_frames with frame_count=0 returns empty list."""
    engine = FakeEngineAdapter()
    result = await engine.generate_frames("test", b"\x00" * 1600, 0)
    assert result == []
