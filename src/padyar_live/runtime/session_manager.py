from __future__ import annotations

from datetime import UTC, datetime, timedelta

from padyar_live.models.schemas import Session, SessionConfig, SessionCreateRequest, SessionStatus


class SessionManager:
    SESSION_TTL = timedelta(minutes=30)
    IDLE_TIMEOUT = timedelta(minutes=5)

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, request: SessionCreateRequest) -> Session:
        config = SessionConfig(
            avatar_id=request.avatar_id,
            fps=request.fps,
            language=request.language,
            engine_url=request.engine_url,
        )
        session = Session(config=config)
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if self._is_expired(session):
            self.close(session_id)
            return None
        return session

    def touch(self, session_id: str) -> bool:
        """Mark session as recently active."""
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.last_active_at = datetime.now(UTC)
        if session.status == SessionStatus.IDLE:
            session.status = SessionStatus.ACTIVE
        return True

    def close(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.status = SessionStatus.CLOSED
        return True

    def mark_error(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.status = SessionStatus.ERROR
        return True

    def list_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def list_active(self) -> list[Session]:
        return [s for s in self._sessions.values() if s.status == SessionStatus.ACTIVE]

    def cleanup_expired(self) -> int:
        """Remove closed and expired sessions. Returns count removed."""
        to_remove = [
            sid for sid, s in self._sessions.items()
            if s.status == SessionStatus.CLOSED or self._is_expired(s)
        ]
        for sid in to_remove:
            del self._sessions[sid]
        return len(to_remove)

    def mark_idle_sessions(self) -> int:
        """Transition idle-timed-out sessions to IDLE status. Returns count transitioned."""
        now = datetime.now(UTC)
        count = 0
        for session in self._sessions.values():
            if session.status != SessionStatus.ACTIVE:
                continue
            if now - session.last_active_at > self.IDLE_TIMEOUT:
                session.status = SessionStatus.IDLE
                count += 1
        return count

    def _is_expired(self, session: Session) -> bool:
        if session.status == SessionStatus.CLOSED:
            return True
        now = datetime.now(UTC)
        return now - session.created_at > self.SESSION_TTL
