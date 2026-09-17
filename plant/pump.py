"""
Pump actuator model with first-order dynamic lag.
Formula: du/dt = (u_command - u) / tau
"""

import core.config as cfg


class PumpActuator:
    def __init__(self, tau: float = cfg.PUMP_TAU):
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

    def get_flow_rate(self) -> float:
        return self.get_inflow()

    def get_actual_pct(self) -> float:
        return self.actual_pct

    def get_inflow(self) -> float:
        return self.actual_pct * cfg.MAX_PUMP_FLOW
