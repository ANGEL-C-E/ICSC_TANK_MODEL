"""
Valve actuator model with first-order dynamic lag.
Formula: du/dt = (u_command - u) / tau
"""

import math
import core.config as cfg


class ValveActuator:
    def __init__(self, tau: float = cfg.VALVE_TAU):
        self.tau = tau
        self.target_pct = 0.0
        self.actual_pct = 0.0

    def set_target(self, target_pct: float):
        self.target_pct = max(0.0, min(1.0, float(target_pct)))

    def update(self, dt: float):
        if self.tau <= 0:
            self.actual_pct = self.target_pct
        else:
            self.actual_pct += (self.target_pct - self.actual_pct) * (dt / self.tau)
            self.actual_pct = max(0.0, min(1.0, self.actual_pct))

    def get_actual_pct(self) -> float:
        return self.actual_pct

    def get_outflow(self, level: float) -> float:
        h_ratio = max(level, 0.0) / cfg.MAX_LEVEL
        return self.actual_pct * cfg.MAX_OUTFLOW * math.sqrt(h_ratio)
