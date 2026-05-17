from __future__ import annotations

from typing import TYPE_CHECKING

from padyar_live.models.schemas import MetricsResponse

if TYPE_CHECKING:
    from padyar_live.api.ws import WSHandler
    from padyar_live.runtime.session_manager import SessionManager


class MetricsCollector:
    """Collects runtime metrics from session manager and active WS handlers."""

    def __init__(self) -> None:
        self._session_manager: SessionManager | None = None
        self._ws_handler: WSHandler | None = None
        self._latency_target_ms = 120.0

    def bind(
        self,
        session_manager: SessionManager,
        ws_handler: WSHandler,
        latency_target_ms: float = 120.0,
    ) -> None:
        self._session_manager = session_manager
        self._ws_handler = ws_handler
        self._latency_target_ms = latency_target_ms

    def collect(self) -> MetricsResponse:
        # Aggregate latency from all active schedulers
        total_frames = 0
        fallback_count = 0
        avg_latency = 0.0
        p95_latency = 0.0
        p99_latency = 0.0
        latency_values = []

        if self._ws_handler is not None:
            # Gather from all active schedulers
            schedulers = list(self._ws_handler._active_schedulers.values())
            for scheduler in schedulers:
                tracker = scheduler.latency
                total_frames += tracker.total_frames
                fallback_count += tracker.fallback_count
                if tracker.total_frames > 0:
                    latency_values.append(tracker.avg_latency_ms())

        if latency_values:
            avg_latency = sum(latency_values) / len(latency_values)

        active_sessions = 0
        active_connections = 0
        if self._session_manager is not None:
            active_sessions = len(self._session_manager.list_active())
        if self._ws_handler is not None:
            active_connections = self._ws_handler.active_connection_count

        fallback_rate = fallback_count / total_frames if total_frames > 0 else 0.0

        return MetricsResponse(
            total_frames=total_frames,
            avg_latency_ms=round(avg_latency, 2),
            p95_latency_ms=round(p95_latency, 2),
            p99_latency_ms=round(p99_latency, 2),
            fallback_count=fallback_count,
            fallback_rate=round(fallback_rate, 4),
            within_target=avg_latency <= self._latency_target_ms,
            active_sessions=active_sessions,
            active_connections=active_connections,
        )
