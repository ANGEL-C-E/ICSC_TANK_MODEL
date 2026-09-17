"""
Unit tests for Control Plane, RBAC authorization, and finite Command Registry.
"""

from control.authorization import AuthorizationManager
from control.command_gateway import CommandGateway
from control.command_registry import CommandRegistry
from control.sessions import SessionManager


def test_command_registry_parsing():
    ok, err, payload = CommandRegistry.parse_command("pump 75")
    assert ok is True
    assert payload["action"] == "pump"
    assert payload["value"] == 0.75

    ok_invalid, err_invalid, _ = CommandRegistry.parse_command("pump 200")
    assert ok_invalid is False

    ok_unreg, err_unreg, _ = CommandRegistry.parse_command("shutdown_database")
    assert ok_unreg is False


def test_rbac_authorization():
    # Operator can control pump, but cannot configure or admin
    assert AuthorizationManager.is_action_allowed("OPERATOR", "pump") is True
    assert AuthorizationManager.is_action_allowed("OPERATOR", "reset") is False

    # Engineer can reset
    assert AuthorizationManager.is_action_allowed("ENGINEER", "reset") is True


def test_gateway_processing():
    import time
    from core.database import db
    db.log_telemetry({"ts": time.time(), "seq": 9999, "level": 0.5, "pressure": 4905.0, "pump_pct": 0.0, "valve_pct": 0.5, "inflow": 0.0, "outflow": 0.1})

    gateway = CommandGateway(mqtt_client=None)

    # 1. Create operator session
    session = SessionManager.create_session("user-01", "operator_01", "OPERATOR")

    # 2. Authorized command succeeds under safe state
    ok, msg, payload = gateway.process_raw_command(session.token, "valve 50")
    assert ok is True

    ok_pump, msg_pump, payload_pump = gateway.process_raw_command(session.token, "pump 10")
    assert ok_pump is True
    assert payload_pump["value"] == 0.10

    # 3. Unauthorized command for OPERATOR role fails
    ok_unauth, msg_unauth, _ = gateway.process_raw_command(session.token, "reset")
    assert ok_unauth is False
    assert "Authorization denied" in msg_unauth
