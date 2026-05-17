from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException

from padyar_live import __version__
from padyar_live.models.schemas import (
    HealthResponse,
    MetricsResponse,
    SessionCreateRequest,
    SessionCreateResponse,
)
from padyar_live.runtime.session_manager import SessionManager

router = APIRouter()

_start_time = time.monotonic()


def _get_session_manager() -> SessionManager:
    from padyar_live.api.app import get_session_manager
    return get_session_manager()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        uptime_seconds=round(time.monotonic() - _start_time, 1),
    )


@router.post("/session", response_model=SessionCreateResponse)
async def create_session(request: SessionCreateRequest) -> SessionCreateResponse:
    mgr = _get_session_manager()
    session = mgr.create(request)
    return SessionCreateResponse(
        session_id=session.session_id,
        status=session.status,
        ws_url=f"/ws/live?session_id={session.session_id}",
    )


@router.get("/session")
async def list_sessions() -> dict[str, object]:
    mgr = _get_session_manager()
    sessions = mgr.list_sessions()
    return {
        "sessions": [s.model_dump() for s in sessions],
        "total": len(sessions),
    }


@router.get("/session/{session_id}")
async def get_session(session_id: str) -> dict[str, object]:
    mgr = _get_session_manager()
    session = mgr.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump()


@router.delete("/session/{session_id}")
async def close_session(session_id: str) -> dict[str, str]:
    mgr = _get_session_manager()
    if not mgr.close(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "closed", "session_id": session_id}


@router.get("/metrics", response_model=MetricsResponse)
async def metrics() -> MetricsResponse:
    from padyar_live.api.app import get_metrics_collector
    collector = get_metrics_collector()
    return collector.collect()
