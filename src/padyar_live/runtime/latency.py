from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass


@dataclass
class LatencyRecord:
    frame_index: int
    session_id: str
    start_time: float
    end_time: float
    source: str = "engine"

    @property
    def latency_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000


class LatencyTracker:
    def __init__(self, max_records: int = 1000, target_ms: float = 120.0) -> None:
        self._records: deque[LatencyRecord] = deque(maxlen=max_records)
        self._target_ms = target_ms
        self._pending: dict[tuple[str, int], float] = {}

    def start_frame(self, session_id: str, frame_index: int) -> None:
        self._pending[(session_id, frame_index)] = time.monotonic()

    def end_frame(
        self, session_id: str, frame_index: int,
        source: str = "engine",
    ) -> LatencyRecord:
        start = self._pending.pop((session_id, frame_index), time.monotonic())
        record = LatencyRecord(
            frame_index=frame_index,
            session_id=session_id,
            start_time=start,
            end_time=time.monotonic(),
            source=source,
        )
        self._records.append(record)
        return record

    def avg_latency_ms(self, last_n: int = 100) -> float:
        if not self._records:
            return 0.0
        recent = list(self._records)[-last_n:]
        return sum(r.latency_ms for r in recent) / len(recent)

    def p95_latency_ms(self, last_n: int = 100) -> float:
        return self._percentile(0.95, last_n)

    def p99_latency_ms(self, last_n: int = 100) -> float:
        return self._percentile(0.99, last_n)

    def _percentile(self, pct: float, last_n: int) -> float:
        if not self._records:
            return 0.0
        recent = sorted(r.latency_ms for r in list(self._records)[-last_n:])
        idx = int(len(recent) * pct)
        return recent[min(idx, len(recent) - 1)]

    def is_within_target(self) -> bool:
        return self.avg_latency_ms() <= self._target_ms

    @property
    def total_frames(self) -> int:
        return len(self._records)

    @property
    def fallback_count(self) -> int:
        return sum(1 for r in self._records if r.source == "fallback")

    @property
    def fallback_rate(self) -> float:
        if not self._records:
            return 0.0
        return self.fallback_count / len(self._records)
