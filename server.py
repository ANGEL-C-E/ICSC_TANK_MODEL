"""
TankModel: physics engine for the ICSC single-tank plant.

Models the liquid level dynamics via mass balance and Torricelli's law:

    Q_in  = pump_pct  * MAX_PUMP_FLOW
    Q_out = valve_pct * MAX_OUTFLOW * sqrt(level / MAX_LEVEL)
    dh/dt = (Q_in - Q_out) / TANK_AREA
    h(t+dt) = clip(h(t) + dh/dt * dt, 0, MAX_LEVEL)

Shared physical constants live in config.py so the detector's shadow model
runs on exactly the same numbers.
"""

import numpy as np

import config as cfg


class TankModel:
    def __init__(self, level=0.0, valve_pct=0.0, pump_pct=0.0, setpoint=None):
        self.inflow = 0.0
        self.outflow = 0.0
        self.level = level
        self.valve_pct = valve_pct
        self.pump_pct = pump_pct
        self.setpoint = setpoint  # optional target level (m); informational

    # --- Getters ---
    def get_level(self):
        return self.level

    def get_inflow(self):
        return self.inflow

    def get_outflow(self):
        return self.outflow

    def get_valve_pct(self):
        return self.valve_pct

    def get_pump_pct(self):
        return self.pump_pct

    # --- Core dynamics ---
    def calculate_derivative(self):
        return (self.inflow - self.outflow) / cfg.TANK_AREA

    def update(self, dt):
        self.inflow = self.pump_pct * cfg.MAX_PUMP_FLOW
        self.outflow = (
            self.valve_pct
            * cfg.MAX_OUTFLOW
            * np.sqrt(max(self.level, 0.0) / cfg.MAX_LEVEL)
        )
        self.level += self.calculate_derivative() * dt
        self.level = float(np.clip(self.level, 0.0, cfg.MAX_LEVEL))

    # --- Actuators ---
    def set_pump(self, pump_pct):
        self.pump_pct = float(np.clip(pump_pct, 0.0, 1.0))

    def set_valve(self, valve_pct):
        self.valve_pct = float(np.clip(valve_pct, 0.0, 1.0))

    def set_setpoint(self, setpoint):
        self.setpoint = float(np.clip(setpoint, 0.0, cfg.MAX_LEVEL))

    # --- Telemetry ---
    def get_state(self):
        return {
            "level": self.level,
            "inflow": self.inflow,
            "outflow": self.outflow,
            "pump_pct": self.pump_pct,
            "valve_pct": self.valve_pct,
        }
