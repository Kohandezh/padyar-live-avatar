# CLAUDE.md — padyar-live-avatar

## Repository Identity

**Name:** padyar-live-avatar
**Role:** Realtime runtime, orchestration layer, and monorepo host for the PadYar AI Avatar ecosystem.
**Author:** Mohammad Kohandezh — KSF Company (info@ksf.ir)

This repository is NOT:
- An ML inference engine
- A model repository
- The PadYarAvatar cognition/product layer

## Monorepo Structure

```
padyar-live-avatar/
├── src/padyar_live/              Governed realtime runtime package
├── tests/                        Governed runtime test suite (54 tests)
├── mobile/padyar-android/        Android SDK
├── mobile/padyar-ios/            iOS SDK
├── PadYar-LipSync-master/        Historical engine reference (snapshot)
├── res/                          Product/avatar assets
├── docs/                         Architecture and governance docs
├── pyproject.toml                Package config
├── README.md                     Public project doc
├── README_fa.md                  Farsi project doc
├── CLAUDE.md                     This file
├── CONTRIBUTING.md               Contribution rules
├── DEVELOPMENT.md                Dev guide
├── SECURITY.md                   Security policy
├── README.mobile.md              Original mobile README (legacy)
├── README_zh.mobile.md           Chinese mobile README (legacy)
├── LICENSE.mobile                Mobile license (legacy)
└── PRIVACYSTATEMENT.mobile.md    Mobile privacy statement (legacy)
```

## Runtime Layer

`src/padyar_live/` — the governed realtime orchestration package.

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

Runtime features:
- WebSocket streaming at `/ws/live` (bidirectional binary frames)
- Async frame queue with chunk scheduling and backpressure
- Session lifecycle (create, touch, close, TTL expiry, idle detection)
- Latency measurement (per-frame avg, p95, p99, fallback rate)
- Fallback recovery on engine timeout or failure
- REST API: `GET /health`, `POST /session`, `GET /session`, `GET /session/{id}`, `DELETE /session/{id}`, `GET /metrics`

## Mobile SDK Layer

`mobile/` contains PadYar mobile SDKs — NOT runtime code.

- `mobile/padyar-android/` — Android SDK (Gradle, offline 2D avatar, NCNN lip-sync, PCM streaming)
- `mobile/padyar-ios/` — iOS SDK (Xcode, CocoaPods, offline 2D avatar, local rendering)

**Status:** Migrated into monorepo. Build work is paused/stopped. Do NOT resume unless explicitly approved.

## Legacy Engine Reference

`PadYar-LipSync-master/` — a historical snapshot of the PadYar-LipSync Python inference engine.

Contains: MuseTalk v1 and v1.5, Jupyter notebooks, realtime_inference.py, web UI, demo videos.

**This is reference only.** It is not imported, not executed, and not maintained from this repo.

The active PadYar-LipSync engine remains a separate repository.

## Product Assets

`res/` — avatar portrait images and pre-rendered video assets (270p and 540p resolutions).

## Hard Rules

### Forbidden Imports and Dependencies

The runtime (`src/padyar_live/`) must NEVER import or depend on:
- torch, tensorflow, onnxruntime, diffusers, transformers
- whisper, mediapipe, ultralytics
- CUDA logic, model weights, inference code
- celery, redis, kafka-python, ray, kubernetes
- sqlalchemy, mongoengine

Allowed runtime dependencies: FastAPI, Uvicorn, Pydantic
Allowed dev dependencies: pytest, pytest-asyncio, httpx, ruff, black, mypy, pre-commit

### Forbidden Actions

- Import from `mobile/` inside `src/padyar_live/`
- Import from `PadYar-LipSync-master/` inside `src/padyar_live/`
- Add ML framework code to `src/padyar_live/`
- Bypass the EngineAdapter interface
- Resume mobile app build without explicit approval
- Reference legacy avatar names in new public docs

## Governance and Tests

Automated enforcement via test suite (121 tests):

| Test file | What it enforces |
|---|---|
| `test_governance_imports` | No ML framework imports in any src/ file |
| `test_governance_deps` | No ML packages installed in venv |
| `test_governance_architecture` | Adapter contract, layering, no circular deps |
| `test_adapter_contract` | EngineAdapter ABC contract |
| `test_engine` | FakeEngineAdapter returns valid JPEGs |
| `test_latency` | LatencyTracker avg/p95/p99/fallback |
| `test_rest` | All REST endpoints |
| `test_scheduler` | Frame scheduling, backpressure, fallback |
| `test_session` | Session CRUD, TTL, idle, cleanup |
| `test_ws_integration` | Full WebSocket lifecycle |
| `test_adapter_factory` | Factory selection, config from env, API key masking |
| `test_remote_engine_adapter` | RemoteEngineAdapter request/response/error handling |
| `test_mock_engine_service` | Mock engine protocol, frames, latency, determinism |
| `test_runtime_e2e_contract` | Full E2E: env→factory→adapter→mock engine→scheduler |

Architecture docs:
- `docs/ARCHITECTURE.md` — Module layout, data flow, replaceable engine strategy
- `docs/BOUNDARIES.md` — Dependency rules, forbidden/bad examples, rollback strategy
- `docs/ADR/0001-runtime-engine-separation.md` — Why inference is external

## Current Known State

- Branch: `main`
- Runtime: ruff clean, mypy clean, 121/121 tests pass
- Ecosystem repos:
  - **PadYar-LipSync** — production-stable inference engine (separate repo)
  - **padyar-live-avatar** — realtime orchestration (this repo, active development)
  - **PadYarAvatar** — cognition layer (not started yet)
- EngineAdapter ABC is implemented: `generate_frames()` + `health_check()`
- FakeEngineAdapter exists for testing without GPU
- All ML access is through adapter interface only

## Paused Work

- Mobile app build — stopped/paused. Do NOT resume unless explicitly approved.
- Runtime feature development — paused during consolidation phase.

## First Action in Fresh Claude Session

1. Read: `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/BOUNDARIES.md`
2. Run: `git status --short`, `git remote -v`, `git log --oneline -5`
3. Run: `ruff check src/ tests/`, `mypy src/padyar_live --ignore-missing-imports`, `pytest tests/ -q`
4. Report state only. Do NOT implement features without approval.

## Current Status

- Monorepo integration is complete and merged into main.
- Runtime remains ML-free, adapter-only, and governed under src/padyar_live/.
- RemoteEngineAdapter MVP implemented and merged (PR #2). Stdlib-only HTTP client, no new dependencies.
- Runtime adapter selection implemented and merged (PR #3). Env vars: `PADYAR_ENGINE_ADAPTER`, `PADYAR_ENGINE_URL`, `PADYAR_ENGINE_API_KEY`.
- `RuntimeConfig.from_env()` loads config from environment. `create_engine_adapter(config)` selects adapter.
- EngineAdapter contract unchanged: `generate_frames()` + `health_check()`.
- Two adapters available: `FakeEngineAdapter` (testing) and `RemoteEngineAdapter` (production).
- Mock engine service added (PR #4). FastAPI app at `src/padyar_live/devtools/mock_engine.py`, CLI at `scripts/run_mock_engine.py`.
- Runtime E2E contract harness added (PR #5). 33 tests covering full path: `RuntimeConfig.from_env()` → `create_engine_adapter()` → `RemoteEngineAdapter` → Mock Engine Service → `FrameScheduler`. No production code changed. 121/121 tests passing.
- Mobile SDK audit is complete. Direct Duix references were not found.
- Mobile build remains paused and must not resume without explicit approval.
- Technical legacy identifiers inside mobile SDKs must not be renamed blindly.
- Any mobile rebrand work requires a separate approved plan.
- Next implementation phase is not predetermined and requires explicit user approval.

## Attribution

Powered by Mohammad Kohandezh — KSF Company
Contact: info@ksf.ir
