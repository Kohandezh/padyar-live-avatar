# Padyar Live Avatar

**Realtime orchestration layer for the PadYar AI Avatar ecosystem.**

This repository handles WebSocket streaming, async scheduling, session lifecycle, latency tracking, fallback recovery, and engine adapter orchestration.

## What this repo does

- WebSocket streaming (`/ws/live`) — bidirectional binary frames with ping/pong keepalive
- Async frame queue and chunk scheduling with backpressure
- Session lifecycle management (create, touch, close, TTL expiry, idle detection)
- Latency measurement (per-frame avg, p95, p99, fallback rate)
- Failover and fallback on engine failure
- REST API for session management and metrics (`/health`, `/session`, `/metrics`)

## What this repo does NOT do

This repository does **not** contain ML models, UNet, VAE, Whisper, TTS engines, or model weights.

Inference is accessed **only** through the `EngineAdapter` interface. All AI processing happens in the external PadYar-LipSync engine.

## Architecture

```
┌──────────────────┐
│   Client App     │
└────────┬─────────┘
         │ WebSocket / REST
         ▼
┌──────────────────┐
│ padyar-live-     │  ← This repo
│ avatar           │
│                  │
│  FastAPI + WS    │
│  Scheduler       │
│  EngineAdapter   │  ← External calls only
└────────┬─────────┘
         │ HTTP
         ▼
┌──────────────────┐
│ PadYar-LipSync   │  ← Stable inference engine
│ (separate repo)  │
│  UNet, VAE,      │
│  Whisper, TTS    │
└──────────────────┘
```

| Repo | Role | Status |
|------|------|--------|
| **PadYar-LipSync** | Stable inference engine (UNet, VAE, Whisper, TTS, face processing) | Production-stable |
| **padyar-live-avatar** | Realtime orchestration (streaming, scheduling, sessions, latency) | Active development |
| **PadYarAvatar** | Future cognition layer (memory, personality, emotion, agents) | Not started |

## Development

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

### Run locally

```bash
python -m padyar_live
# Server starts on http://0.0.0.0:8000
```

### Checks

```bash
ruff check src/ tests/              # Lint
mypy src/padyar_live --ignore-missing-imports  # Type check
pytest tests/ -v                    # Tests (54 total)
pytest tests/test_governance_*.py   # Architecture governance only
```

### CI

GitHub Actions runs on every push/PR:
- **lint** — ruff
- **typecheck** — mypy
- **test** — pytest (54 tests)
- **architecture** — governance checks (forbidden imports, deps, layering)

### Current validation

```
ruff:   All checks passed
mypy:   Success: no issues found in 18 source files
pytest: 54 passed in 2.77s
```

## Architecture governance

Automated enforcement prevents boundary violations:

| Test | What it enforces |
|------|-----------------|
| `test_governance_imports` | No ML framework imports (`torch`, `transformers`, etc.) |
| `test_governance_deps` | No ML packages installed |
| `test_governance_architecture` | Adapter contract, layering, no circular deps |

See `docs/BOUNDARIES.md` for the full forbidden dependency list and good/bad import examples.

## Documentation

- `docs/ARCHITECTURE.md` — Module layout, data flow, replaceable engine strategy
- `docs/BOUNDARIES.md` — What goes where, forbidden deps, rollback strategy
- `docs/ADR/0001-runtime-engine-separation.md` — Why inference is external
- `DEVELOPMENT.md` — How to add endpoints, adapters, WS message types
- `SECURITY.md` — Attack surface and mitigations
- `CONTRIBUTING.md` — Rules and PR process

## Dependencies

Runtime (minimal):
- FastAPI
- Uvicorn
- Pydantic

Dev:
- pytest, pytest-asyncio, httpx
- ruff, black, mypy
- pre-commit

**Forbidden:** torch, transformers, diffusers, onnxruntime, whisper, mediapipe, ultralytics, celery, redis, kafka

## License

See [LICENSE](LICENSE).

---

Powered by: Mohammad Kohandezh — KSF Company
Contact: info@ksf.ir
