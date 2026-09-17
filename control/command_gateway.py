"""
Command Gateway: central entry point for control requests.

Enforces:
1. Session authentication
2. Role-based Access Control (RBAC) authorization
3. Syntax and parameter range validation via finite CommandRegistry
4. MQTT message dispatch with audit logging in SQLite
"""

import time
from typing import Any, Dict, Tuple

from control.authorization import AuthorizationManager
from control.command_registry import CommandRegistry
from control.sessions import SessionManager
from core.database import db
from core.events import EventType
from core.models import CommandMessage
import mqtt.topics as topics


class CommandGateway:
    def __init__(self, mqtt_client=None):
        self.mqtt_client = mqtt_client

    def process_raw_command(self, token: str, raw_line: str, source: str = "cli") -> Tuple[bool, str, Dict[str, Any]]:
        """Parse, authenticate, authorize, and submit a command line string."""
        # 1. Session authentication
        session = SessionManager.validate_session(token)
        if not session:
            db.log_audit_event(
                event_type=EventType.AUTH_FAILURE,
                action="command_submission",
                status="rejected",
                details={"reason": "Invalid or expired session token", "raw_command": raw_line}
            )
            return False, "Authentication failed: invalid or expired session token.", {}

        # 2. Syntax & Command Vocabulary parsing
        ok, err, payload = CommandRegistry.parse_command(raw_line)
        if not ok:
            db.log_audit_event(
                event_type=EventType.COMMAND_REJECTED,
                action="parse_command",
                status="rejected",
                user_id=session["user_id"],
                session_id=session["token"],
                details={"reason": err, "raw_command": raw_line}
            )
            return False, f"Command syntax error: {err}", {}

        # 3. RBAC authorization check
        action = payload.get("command") or payload.get("action")
        if not AuthorizationManager.is_action_allowed(session["role"], action):
            db.log_audit_event(
                event_type=EventType.AUTHORIZATION_FAILURE,
                action=action,
                status="denied",
                user_id=session["user_id"],
                session_id=session["token"],
                details={"role": session["role"], "reason": "Insufficient role capabilities"}
            )
            return False, f"Authorization denied: Role '{session['role']}' cannot execute '{action}'.", {}

        # 4. Construct CommandMessage object
        cmd_msg = CommandMessage(
            command_id=f"cmd-{int(time.time() * 1000)}",
            timestamp=time.time(),
            session_id=session["token"],
            user_id=session["user_id"],
            role=session["role"],
            source=source,
            command=action,
            value=payload.get("value"),
            setpoint=payload.get("setpoint"),
            label=payload.get("label", ""),
        )

        msg_dict = cmd_msg.to_dict()

        # 5. Pre-Actuation Process-Aware Security Inspection (IPS)
        from security.detector import AnomalyDetector
        detector = getattr(self, "_detector", None)
        if detector is None:
            detector = AnomalyDetector()
            self._detector = detector

        recent_t = db.get_recent_telemetry(limit=1)
        if recent_t:
            plant_state = {
                "h": recent_t[0]["level"],
                "pressure": recent_t[0]["pressure"],
                "pump": recent_t[0]["pump_pct"],
                "valve": recent_t[0]["valve_pct"],
            }
        else:
            plant_state = None

        is_blocked, reason, alerts = detector.evaluate_command_pre_actuation(msg_dict, plant_state)

        if is_blocked:
            db.log_audit_event(
                event_type=EventType.ATTACK_BLOCKED,
                action=action,
                status="blocked",
                user_id=session["user_id"],
                session_id=session["token"],
                details={"reason": reason, "command": msg_dict}
            )
            if self.mqtt_client:
                for a in alerts:
                    self.mqtt_client.publish_json(topics.TOPIC_ALERTS, a.to_dict())

            return False, f"[SECURITY INTERLOCK] Command BLOCKED: {reason}", msg_dict

        # 6. Publish to MQTT bus if client is attached and command is safe
        if self.mqtt_client:
            self.mqtt_client.publish_json(topics.TOPIC_COMMANDS, msg_dict)

        # 7. Record audit event in SQLite
        db.log_audit_event(
            event_type=EventType.COMMAND_ACCEPTED,
            action=action,
            status="accepted",
            user_id=session["user_id"],
            session_id=session["token"],
            details=msg_dict
        )

        return True, "Command accepted and published to control bus.", msg_dict
