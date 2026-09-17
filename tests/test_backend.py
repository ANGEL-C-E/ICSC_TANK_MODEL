"""
Unit tests for Backend API and intentional authorization flaw exploitation under ADVISORY mode.
"""

import time
from backend.api import BackendAPI
from control.command_gateway import CommandGateway
from core.database import db


def test_backend_auth_and_vulnerability_exploit():
    db.log_telemetry({"ts": time.time(), "seq": 9999, "level": 0.5, "pressure": 4905.0, "pump_pct": 0.0, "valve_pct": 0.5, "inflow": 0.0, "outflow": 0.1})

    gateway = CommandGateway(mqtt_client=None)
    api = BackendAPI(gateway)

    # 1. Login as guest user 'attacker_01'
    ok, msg, auth_res = api.login("attacker_01", "guest")
    assert ok is True
    guest_token = auth_res["token"]
    assert auth_res["role"] == "GUEST"

    # 2. Direct command submission via standard route fails (RBAC blocks GUEST)
    ok_direct, msg_direct, _ = api.submit_command(guest_token, "pump 50")
    assert ok_direct is False
    assert "Authorization denied" in msg_direct

    # 3. Submission via vulnerable backend endpoint succeeds (authorization bypass exploit)
    ok_vuln, msg_vuln, res = api.submit_vulnerable_command(guest_token, "pump 10")
    assert ok_vuln is True
    assert "[EXPLOIT SUCCESSFUL]" in msg_vuln
    assert res["value"] == 0.10

    # 4. In ADVISORY mode, dangerous commands execute while generating engineer security advisories
    db.log_telemetry({"ts": time.time(), "seq": 10000, "level": 0.85, "pressure": 8338.5, "pump_pct": 0.0, "valve_pct": 0.0, "inflow": 0.0, "outflow": 0.0})
    ok_attack, msg_attack, res_attack = api.submit_vulnerable_command(guest_token, "pump 100")
    assert ok_attack is True
    assert res_attack["value"] == 1.0
