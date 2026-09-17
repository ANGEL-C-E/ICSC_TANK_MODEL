"""
Sensor suite with Gaussian measurement noise and fault injection capabilities.
Formula: y_t = h_t + bias + N(0, sigma^2)
"""

import random
from typing import Optional
import core.config as cfg


class LevelSensor:
    def __init__(self, noise_std: float = cfg.SENSOR_NOISE_STD):
        self.noise_std = noise_std
        self.bias = 0.0
        self.frozen_value: Optional[float] = None
        self.fault_mode: str = "NORMAL"  # "NORMAL", "FREEZE", "BIAS", "NOISY"

    def read_level(self, true_level: float) -> float:
        if self.fault_mode == "FREEZE":
            if self.frozen_value is None:
                self.frozen_value = true_level
            return self.frozen_value

        noise = random.gauss(0.0, self.noise_std) if self.noise_std > 0 else 0.0
        measured = true_level + self.bias + noise
        return max(0.0, min(cfg.MAX_LEVEL, float(measured)))

    def inject_freeze(self, freeze_val: Optional[float] = None):
        self.fault_mode = "FREEZE"
        self.frozen_value = freeze_val

    def clear_faults(self):
        self.fault_mode = "NORMAL"
        self.bias = 0.0
        self.frozen_value = None


class PressureSensor:
    def __init__(self, noise_std: float = 10.0):  # Pa
        self.noise_std = noise_std
        self.fault_mode: str = "NORMAL"

    def read_pressure(self, true_level: float) -> float:
        true_pressure = cfg.RHO * cfg.G * true_level
        noise = random.gauss(0.0, self.noise_std) if self.noise_std > 0 else 0.0
        return max(0.0, float(true_pressure + noise))
