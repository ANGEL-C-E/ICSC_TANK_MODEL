"""
Unit tests for SQLite Database persistence manager.
"""

import os
import tempfile
import time
import pytest

from core.database import DatabaseManager


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_mgr = DatabaseManager(db_path=path)
    yield db_mgr
    if os.path.exists(path):
        os.remove(path)


def test_user_authentication(temp_db):
    user = temp_db.authenticate_user("operator_01", "operator123")
    assert user is not None
    assert user["username"] == "operator_01"
    assert user["role"] == "OPERATOR"

    invalid_user = temp_db.authenticate_user("operator_01", "wrongpassword")
    assert invalid_user is None


def test_session_management(temp_db):
    user = temp_db.authenticate_user("engineer_01", "engineer123")
    token = temp_db.create_session(user["user_id"], user["username"], user["role"], ttl_seconds=10.0)
    assert token.startswith("sess-")

    session = temp_db.validate_session(token)
    assert session is not None
    assert session["username"] == "engineer_01"

    temp_db.invalidate_session(token)
    invalid_sess = temp_db.validate_session(token)
    assert invalid_sess is None


def test_telemetry_and_audit_logging(temp_db):
    telemetry = {
        "ts": time.time(),
        "seq": 1,
        "level": 0.55,
        "pressure": 5395.5,
        "pump_pct": 0.5,
        "valve_pct": 0.2,
        "inflow": 0.25,
        "outflow": 0.1,
    }
    temp_db.log_telemetry(telemetry, operating_mode="RUNNING")

    logs = temp_db.get_recent_telemetry(limit=10)
    assert len(logs) == 1
    assert logs[0]["level"] == 0.55

    temp_db.log_audit_event("LOGIN", "login", "success", user_id="user-01", session_id="sess-123")
    events = temp_db.get_recent_audit_events(limit=10)
    assert len(events) == 1
    assert events[0]["event_type"] == "LOGIN"
