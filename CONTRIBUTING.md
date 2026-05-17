# Contributing to padyar-live-avatar

## Architecture boundary

This repo is the **realtime orchestration layer** only. It does NOT contain AI inference code.

Before contributing, read:
- `docs/ARCHITECTURE.md` — module layout and data flow
- `docs/BOUNDARIES.md` — what goes where and why
- `docs/ADR/0001-runtime-engine-separation.md` — why inference is external

## Hard rules

1. **No ML imports.** `torch`, `transformers`, `diffusers`, `onnxruntime`, `whisper`, etc. are forbidden. A test will fail.
2. **No engine internals.** Use `EngineAdapter` interface only. Never reach into PadYar-LipSync internals.
3. **No new dependencies** without approval. State the problem, why stdlib can't solve it, and confirm it doesn't violate boundaries.
4. **No distributed systems.** No Redis, Celery, Kafka, Ray. We're in single-node phase.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Before pushing

```bash
# All of these must pass
ruff check src/ tests/
mypy src/padyar_live --ignore-missing-imports
pytest tests/ -v
```

## Commit style

- Small, focused commits
- One concern per commit
- Imperative mood: "add WebSocket ping loop" not "added ping loop"

## PR process

1. Create branch from main
2. Make changes
3. Run all checks locally
4. Open PR — CI will run lint, typecheck, tests, architecture checks
5. All CI must pass before merge
