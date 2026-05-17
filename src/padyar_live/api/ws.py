from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from fastapi import WebSocket, WebSocketDisconnect

from padyar_live.models.schemas import WSError
from padyar_live.runtime.config import RuntimeConfig
from padyar_live.runtime.session_manager import SessionManager
from padyar_live.scheduler.frame_scheduler import FrameScheduler

if TYPE_CHECKING:
    from padyar_live.api.ws_handlers import SchedulerFactory

logger = logging.getLogger(__name__)

# WebSocket close codes (custom range 4000-4999)
CLOSE_SESSION_NOT_FOUND = 4004
CLOSE_SESSION_EXPIRED = 4005
CLOSE_SESSION_CLOSED = 4006
CLOSE_MESSAGE_TOO_LARGE = 4009
CLOSE_INTERNAL_ERROR = 4011
CLOSE_NORMAL = 1000


class WSHandler:
    def __init__(
        self,
        session_manager: SessionManager,
        scheduler_factory: SchedulerFactory,
        config: RuntimeConfig | None = None,
    ) -> None:
        self._session_manager = session_manager
        self._scheduler_factory = scheduler_factory
        self._config = config or RuntimeConfig()
        self._active_schedulers: dict[str, FrameScheduler] = {}
        self._active_connections: dict[str, WebSocket] = {}

    @property
    def active_connection_count(self) -> int:
        return len(self._active_connections)

    async def handle(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()

        session = self._session_manager.get(session_id)
        if session is None:
            await _send_error(
                websocket, "session_not_found",
                "Session not found or expired", session_id,
            )
            await websocket.close(
                code=CLOSE_SESSION_NOT_FOUND, reason="Session not found",
            )
            return

        if session.status != "active":
            reason = f"Session is {session.status}"
            await _send_error(websocket, "session_invalid", reason, session_id)
            await websocket.close(code=CLOSE_SESSION_CLOSED, reason=reason)
            return

        scheduler = self._scheduler_factory.create(session.config)
        self._active_schedulers[session_id] = scheduler
        self._active_connections[session_id] = websocket
        self._session_manager.touch(session_id)

        try:
            recv_task = asyncio.create_task(
                _receive_loop(
                    websocket, session_id, scheduler,
                    self._session_manager, self._config,
                )
            )
            send_task = asyncio.create_task(
                _send_loop(websocket, session_id, scheduler)
            )
            ping_task = asyncio.create_task(
                _ping_loop(websocket, session_id, self._config.ws_ping_interval_seconds)
            )

            done, pending = await asyncio.wait(
                [recv_task, send_task, ping_task],
                return_when=asyncio.FIRST_EXCEPTION,
            )

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Re-raise exceptions from done tasks
            for task in done:
                exc = task.exception()
                if exc is not None:
                    raise exc

        except WebSocketDisconnect:
            logger.info("Client disconnected for session %s", session_id)
        except asyncio.CancelledError:
            logger.info("WS cancelled for session %s", session_id)
        except Exception as exc:
            logger.error("WS error for session %s: %s", session_id, exc)
            self._session_manager.mark_error(session_id)
            try:
                await _send_error(websocket, "internal_error", str(exc), session_id)
                await websocket.close(code=CLOSE_INTERNAL_ERROR, reason="Internal error")
            except Exception:
                pass
        finally:
            scheduler.stop()
            self._active_schedulers.pop(session_id, None)
            self._active_connections.pop(session_id, None)
            self._session_manager.close(session_id)

    def get_scheduler(self, session_id: str) -> FrameScheduler | None:
        return self._active_schedulers.get(session_id)


async def _receive_loop(
    websocket: WebSocket,
    session_id: str,
    scheduler: FrameScheduler,
    session_manager: SessionManager,
    config: RuntimeConfig,
) -> None:
    """Receive binary audio from client and submit to scheduler."""
    while True:
        raw = await websocket.receive_bytes()

        if len(raw) > config.max_message_size_bytes:
            await _send_error(
                websocket, "message_too_large",
                f"Max {config.max_message_size_bytes} bytes, got {len(raw)}",
                session_id,
            )
            continue

        session_manager.touch(session_id)
        await scheduler.submit_audio(session_id, raw)


async def _send_loop(
    websocket: WebSocket,
    session_id: str,
    scheduler: FrameScheduler,
) -> None:
    """Send generated frames back to client as binary with metadata header."""
    while True:
        frames = await scheduler.get_next_frames()
        for i, frame_data in enumerate(frames):
            header = json.dumps({
                "index": i,
                "session_id": session_id,
            }).encode()
            await websocket.send_bytes(header + b"\x00" + frame_data)


async def _ping_loop(
    websocket: WebSocket,
    session_id: str,
    interval: float,
) -> None:
    """Send periodic pings to keep connection alive and detect dead peers."""
    while True:
        await asyncio.sleep(interval)
        try:
            await websocket.send_json({"type": "ping"})
        except Exception:
            logger.debug("Ping failed for session %s — connection likely dead", session_id)
            break


async def _send_error(
    websocket: WebSocket,
    code: str,
    message: str,
    session_id: str = "",
) -> None:
    """Send a structured error message over WebSocket."""
    try:
        error = WSError(code=code, message=message, session_id=session_id)
        await websocket.send_json({"type": "error", **error.model_dump()})
    except Exception:
        pass
