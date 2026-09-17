"""
Audit event models and type definitions.
"""

from dataclasses import dataclass, field
import json
import time
from typing import Any, Dict, Optional


class EventType:
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    AUTH_FAILURE = "AUTH_FAILURE"
    AUTHORIZATION_FAILURE = "AUTHORIZATION_FAILURE"
    BACKEND_ACCESS = "BACKEND_ACCESS"
    COMMAND_RECEIVED = "COMMAND_RECEIVED"
    COMMAND_ACCEPTED = "COMMAND_ACCEPTED"
    COMMAND_REJECTED = "COMMAND_REJECTED"
    ACTUATOR_CHANGED = "ACTUATOR_CHANGED"
    TELEMETRY_RECEIVED = "TELEMETRY_RECEIVED"
    ALARM_RAISED = "ALARM_RAISED"
    ALARM_CLEARED = "ALARM_CLEARED"
    ATTACK_BLOCKED = "ATTACK_BLOCKED"
    SAFETY_INTERLOCK_TRIPPED = "SAFETY_INTERLOCK_TRIPPED"
    MAINTENANCE_ENTERED = "MAINTENANCE_ENTERED"
    MAINTENANCE_EXITED = "MAINTENANCE_EXITED"


@dataclass
class AuditEvent:
    event_type: str
    action: str
    status: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": round(self.timestamp, 4),
            "event_type": self.event_type,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "action": self.action,
            "status": self.status,
            "details": self.details or {},
        }

    def render(self) -> str:
        ts_str = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        user_str = self.user_id or "ANONYMOUS"
        return f"[{ts_str}] [{self.event_type}] user={user_str} action={self.action} status={self.status}"
