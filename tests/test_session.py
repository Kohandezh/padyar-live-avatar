from datetime import UTC, datetime, timedelta

from padyar_live.models.schemas import SessionCreateRequest, SessionStatus
from padyar_live.runtime.session_manager import SessionManager


def test_create_session():
    mgr = SessionManager()
    session = mgr.create(SessionCreateRequest(avatar_id="test"))
    assert session.session_id
    assert session.status == SessionStatus.ACTIVE


def test_get_session():
    mgr = SessionManager()
    created = mgr.create(SessionCreateRequest())
    found = mgr.get(created.session_id)
    assert found is not None
    assert found.session_id == created.session_id


def test_get_session_not_found():
    mgr = SessionManager()
    assert mgr.get("nonexistent") is None


def test_close_session():
    mgr = SessionManager()
    session = mgr.create(SessionCreateRequest())
    assert mgr.close(session.session_id) is True
    assert session.status == SessionStatus.CLOSED


def test_close_nonexistent():
    mgr = SessionManager()
    assert mgr.close("nonexistent") is False


def test_mark_error():
    mgr = SessionManager()
    session = mgr.create(SessionCreateRequest())
    mgr.mark_error(session.session_id)
    assert session.status == SessionStatus.ERROR


def test_touch_session():
    mgr = SessionManager()
    session = mgr.create(SessionCreateRequest())
    old_time = session.last_active_at
    import time
    time.sleep(0.01)
    mgr.touch(session.session_id)
    assert session.last_active_at > old_time


def test_list_sessions():
    mgr = SessionManager()
    mgr.create(SessionCreateRequest(avatar_id="a"))
    mgr.create(SessionCreateRequest(avatar_id="b"))
    mgr.create(SessionCreateRequest(avatar_id="c"))
    assert len(mgr.list_sessions()) == 3
    assert len(mgr.list_active()) == 3


def test_cleanup_expired():
    mgr = SessionManager()
    session = mgr.create(SessionCreateRequest())
    mgr.close(session.session_id)
    removed = mgr.cleanup_expired()
    assert removed == 1
    assert mgr.get(session.session_id) is None


def test_expired_session_returns_none():
    mgr = SessionManager()
    session = mgr.create(SessionCreateRequest())
    # Manually expire
    session.created_at = datetime.now(UTC) - timedelta(hours=1)
    assert mgr.get(session.session_id) is None
    assert session.status == SessionStatus.CLOSED


def test_mark_idle_sessions():
    mgr = SessionManager()
    session = mgr.create(SessionCreateRequest())
    session.last_active_at = datetime.now(UTC) - timedelta(minutes=10)
    count = mgr.mark_idle_sessions()
    assert count == 1
    assert session.status == SessionStatus.IDLE
