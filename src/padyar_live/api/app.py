from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request, WebSocket
from fastapi.responses import JSONResponse

from padyar_live.adapters.engine import EngineAdapter
from padyar_live.adapters.factory import create_engine_adapter
from padyar_live.api.metrics import MetricsCollector
from padyar_live.api.routes import router as rest_router
from padyar_live.api.ws import WSHandler
from padyar_live.api.ws_handlers import SchedulerFactory
from padyar_live.runtime.config import RuntimeConfig
from padyar_live.runtime.session_manager import SessionManager

logger = logging.getLogger(__name__)

_session_manager: SessionManager | None = None
_ws_handler: WSHandler | None = None
_metrics_collector: MetricsCollector | None = None


def get_session_manager() -> SessionManager:
    assert _session_manager is not None, "App not initialized"
    return _session_manager


def get_ws_handler() -> WSHandler:
    assert _ws_handler is not None, "App not initialized"
    return _ws_handler


def get_metrics_collector() -> MetricsCollector:
    assert _metrics_collector is not None, "App not initialized"
    return _metrics_collector


def create_app(
    config: RuntimeConfig | None = None,
    engine: EngineAdapter | None = None,
) -> FastAPI:
    global _session_manager, _ws_handler, _metrics_collector

    config = config or RuntimeConfig.from_env()
    _session_manager = SessionManager()

    engine = engine or create_engine_adapter(config)
    factory = SchedulerFactory(
        engine=engine,
        chunk_size=config.chunk_size,
        queue_max_size=config.queue_max_size,
        engine_timeout=config.engine_timeout_seconds,
        fallback_enabled=config.fallback_enabled,
        latency_target_ms=config.latency_target_ms,
    )
    _ws_handler = WSHandler(_session_manager, factory, config)

    _metrics_collector = MetricsCollector()
    _metrics_collector.bind(
        _session_manager,
        _ws_handler,
        latency_target_ms=config.latency_target_ms,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        logger.info("PadYar Live Avatar starting on %s:%d", config.host, config.port)
        yield
        logger.info("PadYar Live Avatar shutting down")
        # Close all active WS connections
        for sid, ws in list(_ws_handler._active_connections.items()):
            try:
                await ws.close(code=1000, reason="Server shutting down")
            except Exception:
                pass

    app = FastAPI(
        title="PadYar Live Avatar",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception,
    ) -> JSONResponse:
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(exc)},
        )

    app.include_router(rest_router, tags=["session"])

    @app.websocket("/ws/live")
    async def ws_live(
        websocket: WebSocket, session_id: str = Query(...),
    ) -> None:
        await get_ws_handler().handle(websocket, session_id)

    return app
