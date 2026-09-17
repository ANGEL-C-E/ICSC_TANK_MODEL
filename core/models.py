"""
Data models and type definitions for the ICSC testbed.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, Optional


@dataclass
class SessionInfo:
    token: str
    user_id: str
    username: str
    role: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 3600.0)
    is_active: bool = True


@dataclass
class CommandMessage:
    command_id: str
    timestamp: float
    session_id: str
    user_id: str
    role: str
    source: str
    command: str  # "pump", "valve", "setpoint", "estop", "reset"
    value: Optional[float] = None
    setpoint: Optional[float] = None
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "command_id": self.command_id,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "role": self.role,
            "source": self.source,
            "command": self.command,
        }
        if self.value is not None:
            d["value"] = self.value
        if self.setpoint is not None:
            d["setpoint"] = self.setpoint
        if self.label:
            d["label"] = self.label
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommandMessage":
        return cls(
            command_id=data.get("command_id", f"cmd-{int(time.time()*1000)}"),
            timestamp=data.get("timestamp", time.time()),
            session_id=data.get("session_id", ""),
            user_id=data.get("user_id", "anonymous"),
            role=data.get("role", "GUEST"),
            source=data.get("source", "cli"),
            command=data.get("command", data.get("action", "unknown")),
            value=data.get("value"),
            setpoint=data.get("setpoint"),
            label=data.get("label", ""),
        )


@dataclass
class CommandACK:
    command_id: str
    status: str  # "accepted", "rejected", "applied"
    reason: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "status": self.status,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class TelemetryMessage:
    ts: float
    seq: int
    level: float
    pressure: float
    pump_pct: float
    valve_pct: float
    inflow: float
    outflow: float
    operating_mode: str = "RUNNING"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": round(self.ts, 4),
            "seq": self.seq,
            "level": round(self.level, 6),
            "pressure": round(self.pressure, 3),
            "pump_pct": round(self.pump_pct, 4),
            "valve_pct": round(self.valve_pct, 4),
            "inflow": round(self.inflow, 6),
            "outflow": round(self.outflow, 6),
            "operating_mode": self.operating_mode,
        }
