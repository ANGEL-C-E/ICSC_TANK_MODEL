"""
Physical Tank ODE physics engine integrating Mass Balance & Torricelli's Law.

Q_in  = pump.get_inflow()
Q_out = valve.get_outflow(level)
dh/dt = (Q_in - Q_out) / TANK_AREA
h(t+dt) = clip(h(t) + dh/dt * dt, 0, MAX_LEVEL)
"""

import core.config as cfg
from plant.pump import PumpActuator
from plant.sensors import LevelSensor, PressureSensor
from plant.valve import ValveActuator


class TankProcess:
    def __init__(self, initial_level: float = 0.5):
        self.level = float(initial_level)
        self.setpoint: Optional[float] = None
        self.pump = PumpActuator()
        self.valve = ValveActuator()
        self.level_sensor = LevelSensor()
        self.pressure_sensor = PressureSensor()
        self.inflow = 0.0
        self.outflow = 0.0

    def update(self, dt: float):
        # 1. Update actuator dynamics
        self.pump.update(dt)
        self.valve.update(dt)

        # 2. Calculate flow rates
        self.inflow = self.pump.get_inflow()
        self.outflow = self.valve.get_outflow(self.level)

        # 3. Calculate derivative dh/dt
        dh_dt = (self.inflow - self.outflow) / cfg.TANK_AREA

        # 4. Forward Euler Integration & Hard Boundary Clip
        self.level += dh_dt * dt
        self.level = max(0.0, min(cfg.MAX_LEVEL, float(self.level)))


    def get_measured_state(self) -> dict:
        measured_h = self.level_sensor.read_level(self.level)
        measured_p = self.pressure_sensor.read_pressure(measured_h)
        return {
            "level": measured_h,
            "true_level": self.level,
            "pressure": measured_p,
            "pump_pct": self.pump.get_actual_pct(),
            "pump_target": self.pump.target_pct,
            "valve_pct": self.valve.get_actual_pct(),
            "valve_target": self.valve.target_pct,
            "inflow": self.inflow,
            "outflow": self.outflow,
            "setpoint": self.setpoint,
        }
