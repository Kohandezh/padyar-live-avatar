# Development Guide

## Repo structure

```
src/padyar_live/
├── api/              FastAPI routes, WebSocket handler, metrics
├── adapters/         EngineAdapter ABC + FakeEngineAdapter
├── runtime/          Config, session manager, latency tracker
├── scheduler/        Async frame queue and chunk scheduler
└── models/           Pydantic schemas for all I/O
```

## Running locally

```bash
source .venv/bin/activate
python -m padyar_live
# Server starts on http://0.0.0.0:8000
```

## Running tests

```bash
pytest tests/ -v                    # All tests
pytest tests/test_governance_*.py   # Architecture checks only
pytest tests/test_ws_integration.py # WebSocket lifecycle only
```

## Adding a new REST endpoint

1. Add Pydantic model to `models/schemas.py`
2. Add route to `api/routes.py`
3. Add test to `tests/test_rest.py`

## Adding a new engine adapter

1. Subclass `EngineAdapter` in a new file under `adapters/`
2. Implement `generate_frames()` and `health_check()`
3. Pass to `create_app(engine=YourAdapter())`
4. Add test to `tests/test_adapter_contract.py`

## Adding a new WebSocket message type

1. Add schema to `models/schemas.py`
2. Handle in `api/ws.py` receive or send loop
3. Add integration test to `tests/test_ws_integration.py`

## Governance tests

Four test files enforce architecture:

| File | What it checks |
|------|---------------|
| `test_governance_imports.py` | No ML framework imports in any .py file |
| `test_governance_deps.py` | No ML packages installed |
| `test_governance_architecture.py` | Layering, adapter contract, no circular imports |

These run in CI on every push. They cannot be bypassed.

## Pre-commit hooks

```bash
pre-commit install   # Install hooks
pre-commit run --all-files  # Run manually
```

Hooks run: black (format), ruff (lint), mypy (types), trailing-whitespace, large-file check.
