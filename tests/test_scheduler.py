import asyncio

import pytest

from padyar_live.adapters.engine import EngineAdapter, FakeEngineAdapter
from padyar_live.runtime.latency import LatencyTracker
from padyar_live.scheduler.frame_scheduler import FrameScheduler


@pytest.mark.asyncio
async def test_scheduler_produces_frames():
    engine = FakeEngineAdapter()
    tracker = LatencyTracker()
    scheduler = FrameScheduler(engine, fps=25, chunk_size=4, latency_tracker=tracker)

    await scheduler.submit_audio("s1", b"\x00" * 1600)
    frames = await scheduler.get_next_frames()

    assert len(frames) == 4
    for f in frames:
        assert isinstance(f, bytes)


@pytest.mark.asyncio
async def test_scheduler_tracks_latency():
    engine = FakeEngineAdapter()
    tracker = LatencyTracker()
    scheduler = FrameScheduler(engine, fps=25, chunk_size=4, latency_tracker=tracker)

    await scheduler.submit_audio("s1", b"\x00" * 1600)
    await scheduler.get_next_frames()

    assert tracker.total_frames == 4
    assert tracker.avg_latency_ms() > 0


@pytest.mark.asyncio
async def test_scheduler_fallback_on_timeout():
    class SlowEngine(EngineAdapter):
        async def generate_frames(self, session_id, audio_chunk, frame_count):
            await asyncio.sleep(10)
            return []
        async def health_check(self):
            return True

    engine = SlowEngine()
    scheduler = FrameScheduler(engine, engine_timeout=0.1, fallback_enabled=True)

    await scheduler.submit_audio("s1", b"\x00" * 1600)
    frames = await scheduler.get_next_frames()

    assert len(frames) == 4
    assert all(f == b"" for f in frames)


@pytest.mark.asyncio
async def test_scheduler_fallback_disabled_raises():
    class FailingEngine(EngineAdapter):
        async def generate_frames(self, session_id, audio_chunk, frame_count):
            raise RuntimeError("engine broken")
        async def health_check(self):
            return True

    engine = FailingEngine()
    scheduler = FrameScheduler(engine, engine_timeout=5.0, fallback_enabled=False)

    with pytest.raises(RuntimeError, match="Engine failed"):
        await scheduler.submit_audio("s1", b"\x00" * 1600)


@pytest.mark.asyncio
async def test_scheduler_concurrent_submit():
    engine = FakeEngineAdapter()
    scheduler = FrameScheduler(engine, fps=25, chunk_size=4)

    # Submit multiple chunks concurrently
    tasks = [
        scheduler.submit_audio("s1", b"\x00" * 1600)
        for _ in range(3)
    ]
    await asyncio.gather(*tasks)

    # Should get 3 batches back
    for _ in range(3):
        frames = await scheduler.get_next_frames()
        assert len(frames) == 4


@pytest.mark.asyncio
async def test_scheduler_backpressure():
    engine = FakeEngineAdapter()
    scheduler = FrameScheduler(engine, queue_max_size=2, chunk_size=4)

    # Fill queue beyond capacity
    for _ in range(4):
        await scheduler.submit_audio("s1", b"\x00" * 1600)

    # Should still be able to get frames (oldest dropped)
    frames = await scheduler.get_next_frames()
    assert len(frames) == 4


@pytest.mark.asyncio
async def test_scheduler_stop():
    engine = FakeEngineAdapter()
    scheduler = FrameScheduler(engine)
    assert not scheduler.is_running

    await scheduler.submit_audio("s1", b"\x00" * 1600)
    assert scheduler.is_running

    scheduler.stop()
    assert not scheduler.is_running
