from __future__ import annotations

from padyar_live.adapters.engine import EngineAdapter, FakeEngineAdapter
from padyar_live.models.schemas import SessionConfig
from padyar_live.runtime.latency import LatencyTracker
from padyar_live.scheduler.frame_scheduler import FrameScheduler


class SchedulerFactory:
    """Creates FrameScheduler instances per session."""

    def __init__(
        self,
        engine: EngineAdapter | None = None,
        chunk_size: int = 4,
        queue_max_size: int = 120,
        engine_timeout: float = 5.0,
        fallback_enabled: bool = True,
        latency_target_ms: float = 120.0,
    ) -> None:
        self._engine = engine or FakeEngineAdapter()
        self._chunk_size = chunk_size
        self._queue_max_size = queue_max_size
        self._engine_timeout = engine_timeout
        self._fallback_enabled = fallback_enabled
        self._latency_target_ms = latency_target_ms

    def create(self, config: SessionConfig) -> FrameScheduler:
        tracker = LatencyTracker(target_ms=self._latency_target_ms)
        return FrameScheduler(
            engine=self._engine,
            fps=config.fps,
            chunk_size=self._chunk_size,
            queue_max_size=self._queue_max_size,
            engine_timeout=self._engine_timeout,
            fallback_enabled=self._fallback_enabled,
            latency_tracker=tracker,
        )
