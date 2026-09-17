"""
TankModel: backwards compatibility wrapper for plant.tank.TankProcess.
"""

from plant.tank import TankProcess


class TankModel:
    def __init__(self, level: float = 0.0, valve_pct: float = 0.0, pump_pct: float = 0.0, setpoint=None):
        self.process = TankProcess(initial_level=level)
        self.process.pump.set_target(pump_pct)
        self.process.valve.set_target(valve_pct)
        self.process.setpoint = setpoint

    @property
    def level(self) -> float:
        return self.process.level

    @level.setter
    def level(self, val: float):
        self.process.level = float(val)

    @property
    def setpoint(self):
        return self.process.setpoint

    @setpoint.setter
    def setpoint(self, val):
        self.process.setpoint = val

    def get_level(self) -> float:
        return self.process.level

    def get_inflow(self) -> float:
        return self.process.inflow

    def get_outflow(self) -> float:
        return self.process.outflow

    def get_valve_pct(self) -> float:
        return self.process.valve.get_actual_pct()

    def get_pump_pct(self) -> float:
        return self.process.pump.get_actual_pct()

    def calculate_derivative(self) -> float:
        return (self.process.inflow - self.process.outflow) / 1.0

    def update(self, dt: float):
        self.process.update(dt)

    def set_pump(self, pump_pct: float):
        self.process.pump.set_target(pump_pct)

    def set_valve(self, valve_pct: float):
        self.process.valve.set_target(valve_pct)

    def set_setpoint(self, setpoint: float):
        self.process.setpoint = float(setpoint)

    def get_state(self) -> dict:
        m = self.process.get_measured_state()
        return {
            "level": m["level"],
            "inflow": m["inflow"],
            "outflow": m["outflow"],
            "pump_pct": m["pump_pct"],
            "valve_pct": m["valve_pct"],
        }
