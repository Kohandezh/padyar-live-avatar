# Security Policy

## Attack surface

This service exposes:
- **REST API** on port 8000 (JSON request/response)
- **WebSocket** on `/ws/live` (binary frames, bidirectional)

## Threats and mitigations

### Unbounded message size (WS)

**Risk:** Client sends multi-GB message, exhausts memory.
**Mitigation:** `RuntimeConfig.max_message_size_bytes` (default 1MB). Enforced in `ws.py` receive loop. Messages exceeding limit are rejected with error frame.

### Unbounded session growth

**Risk:** Thousands of sessions created, memory leak.
**Mitigation:** `SessionManager.SESSION_TTL` (30 min). Expired sessions cleaned up automatically. `cleanup_expired()` available for scheduled runs.

### Engine adapter timeout

**Risk:** Engine hangs, runtime threads accumulate.
**Mitigation:** `RuntimeConfig.engine_timeout_seconds` (5s). `asyncio.wait_for` enforces deadline. Fallback frames returned on timeout.

### No authentication

**Current state:** No auth on any endpoint. Acceptable for single-node development.
**Future:** Add API key or JWT validation when exposing to network.

## What NOT to add

- No file upload endpoints
- No shell execution
- No database connections
- No outbound network calls except to configured engine URL

## Reporting

Report security issues via GitHub Issues or directly to the maintainer.
