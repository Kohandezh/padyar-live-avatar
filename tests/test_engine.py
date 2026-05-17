import pytest

from padyar_live.adapters.engine import FakeEngineAdapter


@pytest.mark.asyncio
async def test_fake_engine_returns_frames():
    engine = FakeEngineAdapter()
    frames = await engine.generate_frames("test-session", b"\x00" * 1600, 4)
    assert len(frames) == 4
    for f in frames:
        assert f.startswith(b"\xff\xd8")  # JPEG magic bytes
        assert f.endswith(b"\xff\xd9")


@pytest.mark.asyncio
async def test_fake_engine_health():
    engine = FakeEngineAdapter()
    assert await engine.health_check() is True
