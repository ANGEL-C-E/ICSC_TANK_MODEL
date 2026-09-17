"""
JSON Schema definitions and payload validators for ICSC bus messages.
"""

from typing import Any, Dict, Tuple
import core.config as cfg


def validate_command_payload(payload: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "Payload must be a JSON object"

    # Support legacy field "action" alongside "command"
    cmd = payload.get("command") or payload.get("action")
    if not cmd or not isinstance(cmd, str):
        return False, "Missing or non-string 'command' field"

    valid_commands = {"pump", "valve", "setpoint", "estop", "reset", "status"}
    if cmd not in valid_commands:
        return False, f"Unrecognized command action: '{cmd}'"

    if cmd in ("pump", "valve"):
        val = payload.get("value")
        if val is None or not isinstance(val, (int, float)) or isinstance(val, bool):
            return False, f"Command '{cmd}' requires numeric 'value' in range [0, 1]"
        if not (0.0 <= float(val) <= 1.0):
            return False, f"Value {val} out of bounds [0.0, 1.0]"

    elif cmd == "setpoint":
        sp = payload.get("setpoint")
        if sp is None or not isinstance(sp, (int, float)) or isinstance(sp, bool):
            return False, "Command 'setpoint' requires numeric 'setpoint' in meters"
        if not (0.0 <= float(sp) <= cfg.MAX_LEVEL):
            return False, f"Setpoint {sp} out of physical bounds [0.0, {cfg.MAX_LEVEL}]"

    return True, ""


def validate_telemetry_payload(payload: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "Payload must be a JSON object"

    level = payload.get("level")
    if level is None or not isinstance(level, (int, float)) or isinstance(level, bool):
        return False, "Missing or non-numeric 'level'"
    if not (0.0 <= float(level) <= cfg.MAX_LEVEL):
        return False, f"Level {level} outside physical tank bounds [0.0, {cfg.MAX_LEVEL}]"

    for field in ("pump_pct", "valve_pct"):
        if field in payload:
            v = payload[field]
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not (0.0 <= float(v) <= 1.0):
                return False, f"Field '{field}' must be numeric in range [0.0, 1.0]"

    return True, ""
