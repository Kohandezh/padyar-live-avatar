import time

from padyar_live.runtime.latency import LatencyTracker


def test_latency_tracker_basic():
    tracker = LatencyTracker(target_ms=200.0)

    tracker.start_frame("s1", 0)
    time.sleep(0.01)
    record = tracker.end_frame("s1", 0)

    assert record.latency_ms >= 5
    assert tracker.total_frames == 1
    assert tracker.avg_latency_ms() >= 5


def test_latency_tracker_target():
    tracker = LatencyTracker(target_ms=200.0)

    tracker.start_frame("s1", 0)
    tracker.end_frame("s1", 0)

    assert tracker.is_within_target()


def test_latency_tracker_fallback_count():
    tracker = LatencyTracker()

    for i in range(4):
        tracker.start_frame("s1", i)
        tracker.end_frame("s1", i, source="fallback")

    assert tracker.fallback_count == 4
    assert tracker.fallback_rate == 1.0


def test_latency_tracker_p95_p99():
    tracker = LatencyTracker()

    for i in range(20):
        tracker.start_frame("s1", i)
        time.sleep(0.001 * (i + 1))
        tracker.end_frame("s1", i)

    p95 = tracker.p95_latency_ms()
    p99 = tracker.p99_latency_ms()
    assert p95 > 0
    assert p99 >= p95


def test_latency_tracker_empty():
    tracker = LatencyTracker()
    assert tracker.avg_latency_ms() == 0.0
    assert tracker.p95_latency_ms() == 0.0
    assert tracker.p99_latency_ms() == 0.0
    assert tracker.fallback_rate == 0.0
