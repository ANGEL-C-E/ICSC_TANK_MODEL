"""
Physics & Shadow Model Detector.

Computes:
1. Process Residuals: r_t = x_{t+1} - shadow_prediction(x_t, u_t)
2. 60-second forward Euler trajectory simulation for future overfill or dry-out prediction
"""

import math
from typing import Dict, Optional, Tuple
import core.config as cfg


class PhysicsDetector:
    def __init__(self):
        self.shadow_h = 0.5
        self.shadow_time = 0.0

    def compute_residual(self, observed_h: float, pump: float, valve: float, dt: float) -> Tuple[float, float]:
        """
        Compute predicted level h_hat and process residual r_t = |observed_h - h_hat|.
        """
        q_in = pump * cfg.MAX_PUMP_FLOW
        q_out = valve * cfg.MAX_OUTFLOW * math.sqrt(max(self.shadow_h, 0.0) / cfg.MAX_LEVEL)
        dh_dt = (q_in - q_out) / cfg.TANK_AREA

        predicted_h = self.shadow_h + dh_dt * dt
        predicted_h = max(0.0, min(cfg.MAX_LEVEL, float(predicted_h)))

        residual = abs(observed_h - predicted_h)

        # Update shadow state
        self.shadow_h = observed_h
        return predicted_h, residual

    @staticmethod
    def forward_simulate(h: float, pump: float, valve: float,
                         horizon: float = cfg.PREDICTION_HORIZON,
                         dt: float = cfg.PREDICTION_DT) -> Tuple[float, Optional[float], Optional[float]]:
        """
        Shadow-simulate the tank into the future; return (h_final, eta_overfill, eta_dry).
        eta_overfill / eta_dry: seconds until safe operating bounds are breached.
        """
        h_sim = h
        eta_overfill = None
        eta_dry = None
        steps = max(1, int(horizon / dt))

        for i in range(1, steps + 1):
            q_in = pump * cfg.MAX_PUMP_FLOW
            q_out = valve * cfg.MAX_OUTFLOW * math.sqrt(max(h_sim, 0.0) / cfg.MAX_LEVEL)
            h_sim += (q_in - q_out) / cfg.TANK_AREA * dt
            h_sim = max(0.0, min(cfg.MAX_LEVEL, h_sim))

            if eta_overfill is None and h_sim >= cfg.MAX_SAFE_HEIGHT:
                eta_overfill = i * dt
            if eta_dry is None and h_sim <= cfg.MIN_SAFE_HEIGHT:
                eta_dry = i * dt

            if h_sim <= 0.0 or h_sim >= cfg.MAX_LEVEL:
                break

        return h_sim, eta_overfill, eta_dry
