# Architecture

## What this repo is

`padyar-live-avatar` is the **realtime orchestration layer** in the PadYar ecosystem. It handles streaming, scheduling, and transport. It does NOT handle AI inference.

This repo is also a **monorepo** hosting mobile SDKs, a historical engine reference, and product assets alongside the governed runtime.

## Monorepo layout

```
padyar-live-avatar/
├── src/padyar_live/              GOVERNED — realtime runtime
├── tests/                        GOVERNED — runtime test suite
├── mobile/padyar-android/        Android SDK (not governed, not imported by runtime)
├── mobile/padyar-ios/            iOS SDK (not governed, not imported by runtime)
├── PadYar-LipSync-master/        Historical engine reference (not governed, not imported)
├── res/                          Product/avatar assets
└── docs/                         Architecture and governance docs
```

Governance scope: `src/padyar_live/` and `tests/` only.
Mobile SDKs, legacy engine reference, and product assets are NOT runtime code.

## Layer interaction

```
┌──────────────────┐
│   Mobile/Web     │  Client
│   App            │
└───────┬──────────┘
        │ WebSocket / REST
        ▼
┌──────────────────┐
│ padyar-live-     │  THIS REPO (runtime)
│ avatar           │
│                  │
│  ┌────────────┐  │
│  │ FastAPI     │  │  REST: /health /session /metrics
│  │ + WS       │  │  WS:   /ws/live
│  └─────┬──────┘  │
│        │         │
│  ┌─────▼──────┐  │
│  │ Frame       │  │  Async queue, chunk scheduling,
│  │ Scheduler   │  │  backpressure, latency tracking
│  └─────┬──────┘  │
│        │         │
│  ┌─────▼──────┐  │
│  │ Engine      │  │  Adapter interface ONLY
│  │ Adapter     │  │  No model code
│  └─────┬──────┘  │
└────────┼─────────┘
         │ HTTP/gRPC (external call)
         ▼
┌──────────────────┐
│ PadYar-LipSync   │  EXTERNAL — separate repo, do not modify from here
│                  │
│  UNet, VAE,      │
│  Whisper, TTS,   │
│  Face processing │
└──────────────────┘

┌──────────────────┐
│ PadYarAvatar     │  FUTURE — not built yet
│ (not built)      │
│ Memory, emotion, │
│ personality,     │
│ cognition        │
└──────────────────┘
```

## Runtime module layout

```
src/padyar_live/
├── api/
│   ├── app.py           FastAPI app factory, lifespan, global error handler
│   ├── routes.py        REST endpoints (/health, /session, /metrics)
│   ├── ws.py            WebSocket handler (ping/pong, close codes, error frames)
│   ├── ws_handlers.py   SchedulerFactory (one scheduler per session)
│   └── metrics.py       MetricsCollector (aggregates from active schedulers)
├── adapters/
│   └── engine.py        EngineAdapter ABC + FakeEngineAdapter
├── runtime/
│   ├── config.py        RuntimeConfig (host, port, timeouts, queue sizes)
│   ├── session_manager.py  Session CRUD, TTL, idle detection, cleanup
│   └── latency.py       LatencyTracker (avg, p95, p99, fallback rate)
├── scheduler/
│   └── frame_scheduler.py  Async queue, chunking, backpressure, fallback
└── models/
    └── schemas.py       Pydantic models for all I/O
```

## Data flow

```
Client sends PCM audio bytes via WS
  → WSHandler._receive_loop
    → SessionManager.touch (keepalive)
    → FrameScheduler.submit_audio
      → EngineAdapter.generate_frames (external call)
      → on timeout/error → fallback frames
      → push to asyncio.Queue (backpressure: drop oldest)
  → WSHandler._send_loop
    ← FrameScheduler.get_next_frames
    ← binary frame with JSON header + JPEG payload
```

## Design principles

1. **Runtime owns orchestration, never inference.** All AI goes through `EngineAdapter`.
2. **Single-node first.** No distributed systems until the single-node path is proven.
3. **Async-native.** Everything is `async def`. No threads, no subprocess pooling.
4. **Fail gracefully.** Fallback frames on engine timeout. Structured errors over WS. Never crash.
5. **Stateless between restarts.** Sessions are in-memory. No database. No persistence needed yet.

## Replaceable engine strategy

The `EngineAdapter` ABC has exactly two methods:

```python
class EngineAdapter(ABC):
    async def generate_frames(self, session_id, audio_chunk, frame_count) -> list[bytes]
    async def health_check(self) -> bool
```

Any engine that implements these two methods plugs in transparently. Current implementations:

| Adapter | Purpose |
|---------|---------|
| `FakeEngineAdapter` | Testing — returns placeholder JPEGs with simulated latency |
| Future: `LipSyncAdapter` | HTTP client to PadYar-LipSync server |
| Future: `GrpcLipSyncAdapter` | gRPC client for lower overhead |

To add a real engine adapter: implement the ABC, pass it to `create_app(engine=...)`. Zero changes to runtime code.

## Attribution

Powered by: Mohammad Kohandezh — KSF Company
Contact: info@ksf.ir
