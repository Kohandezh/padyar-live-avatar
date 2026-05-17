from __future__ import annotations

import asyncio
import logging

from padyar_live.adapters.engine import EngineAdapter
from padyar_live.runtime.latency import LatencyTracker

logger = logging.getLogger(__name__)


class FrameScheduler:
    """Schedules audio chunks for frame generation and streams results."""

    def __init__(
        self,
        engine: EngineAdapter,
        fps: int = 25,
        chunk_size: int = 4,
        queue_max_size: int = 120,
        engine_timeout: float = 5.0,
        fallback_enabled: bool = True,
        latency_tracker: LatencyTracker | None = None,
    ) -> None:
        self._engine = engine
        self._fps = fps
        self._chunk_size = chunk_size
        self._engine_timeout = engine_timeout
        self._fallback_enabled = fallback_enabled
        self._latency = latency_tracker or LatencyTracker()
        self._output_queue: asyncio.Queue[list[bytes]] = asyncio.Queue(maxsize=queue_max_size)
        self._running = False
        self._lock = asyncio.Lock()
        self._frame_counter = 0

    async def submit_audio(self, session_id: str, audio_chunk: bytes) -> None:
        """Submit an audio chunk and generate corresponding frames.

        Thread-safe: concurrent submits are serialized per scheduler.
        Drops oldest batch if queue is full (backpressure).
        """
        if not self._running:
            self._running = True

        async with self._lock:
            frame_count = self._chunk_size
            base_index = self._frame_counter
            self._frame_counter += frame_count

            for i in range(frame_count):
                self._latency.start_frame(session_id, base_index + i)

            try:
                frames = await asyncio.wait_for(
                    self._engine.generate_frames(session_id, audio_chunk, frame_count),
                    timeout=self._engine_timeout,
                )
                for i in range(len(frames)):
                    self._latency.end_frame(session_id, base_index + i, source="engine")
            except TimeoutError:
                logger.warning("Engine timeout for session %s — using fallback", session_id)
                frames = self._fallback(session_id, base_index, frame_count)
            except Exception as exc:
                logger.error("Engine error for session %s: %s", session_id, exc)
                frames = self._fallback(session_id, base_index, frame_count)

            # Backpressure: if queue full, drop oldest
            if self._output_queue.full():
                try:
                    self._output_queue.get_nowait()
                    logger.warning("Queue full — dropped oldest batch for session %s", session_id)
                except asyncio.QueueEmpty:
                    pass

            await self._output_queue.put(frames)

    async def get_next_frames(self) -> list[bytes]:
        """Get the next available frame batch from the output queue."""
        return await self._output_queue.get()

    def get_next_frames_nowait(self) -> list[bytes] | None:
        """Non-blocking peek. Returns None if queue empty."""
        try:
            return self._output_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def _fallback(self, session_id: str, base_index: int, frame_count: int) -> list[bytes]:
        if not self._fallback_enabled:
            raise RuntimeError("Engine failed and fallback is disabled")

        logger.info("Generating fallback frames for session %s", session_id)
        for i in range(frame_count):
            self._latency.end_frame(session_id, base_index + i, source="fallback")
        return [b"" for _ in range(frame_count)]

    def stop(self) -> None:
        self._running = False

    @property
    def latency(self) -> LatencyTracker:
        return self._latency

    @property
    def queue_size(self) -> int:
        return self._output_queue.qsize()

    @property
    def is_running(self) -> bool:
        return self._running
