"""
Behavioral Detector tracking frozen feeds, setpoint drift, and command oscillation patterns.
"""

import time
from typing import Any, Dict, List, Optional
import core.config as cfg

_FROZEN_EPS = 1e-9


class BehavioralDetector:
    def __init__(self):
        self.last_h: Optional[float] = None
        self.frozen_count: int = 0
        self.setpoint_history: List[tuple] = []  # (timestamp, setpoint)
        self.command_timestamps: List[float] = []

    def process_telemetry_behavior(self, h: float, pump_pct: float) -> Optional[Dict[str, Any]]:
        # Frozen feed check while pump is active
        if self.last_h is not None and pump_pct > 0.05:
            if abs(h - self.last_h) < _FROZEN_EPS:
                self.frozen_count += 1
                if self.frozen_count >= cfg.FROZEN_SAMPLES:
                    return {
                        "type": "frozen_feed",
                        "severity": "WARNING",
                        "msg": f"Level frozen at {h:.3f}m for {self.frozen_count} consecutive samples while pump active."
                    }
            else:
                self.frozen_count = 0
        else:
            self.frozen_count = 0

        self.last_h = h
        return None

    def process_setpoint(self, setpoint: float) -> Optional[Dict[str, Any]]:
        now = time.time()
        self.setpoint_history.append((now, setpoint))
        cutoff = now - cfg.SETPOINT_DRIFT_WINDOW
        self.setpoint_history = [(t, s) for (t, s) in self.setpoint_history if t >= cutoff]

        if len(self.setpoint_history) >= 3:
            vals = [s for (_, s) in self.setpoint_history]
            drift = max(vals) - min(vals)
            if drift > cfg.SETPOINT_DRIFT_LIMIT:
                return {
                    "type": "setpoint_drift",
                    "severity": "HIGH",
                    "msg": f"Cumulative setpoint drift of {drift:.2f}m in {cfg.SETPOINT_DRIFT_WINDOW:.0f}s window."
                }
        return None

    def track_command_frequency(self) -> Optional[Dict[str, Any]]:
        now = time.time()
        self.command_timestamps.append(now)
        # Keep timestamps from last 10 seconds
        self.command_timestamps = [t for t in self.command_timestamps if now - t <= 10.0]
        if len(self.command_timestamps) >= 5:
            return {
                "type": "command_oscillation",
                "severity": "HIGH",
                "msg": f"High command frequency ({len(self.command_timestamps)} commands in 10s) detected."
            }
        return None
