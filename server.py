import numpy as np 



constraints = {
    "TANK_AREA": 1.0,  
    "MAX_LEVEL": 10.0,    
    "MAX_PUMP_FLOW" : 0.5, 
    "MAX_OUTFLOW" : 0.4 ,          
 }


class TankModel:
    def __init__(
            self,
            level:float=0.0, 
            valve_pct:float=0.0, 
            pump_pct:float=0.0
        ):

        self.inflow = 0.0
        self.outflow = 0.0 
        self.level = level 
        self.valve_pct = valve_pct 
        self.pump_pct = pump_pct


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

    def calculate_derivative(self):
        dhdt = (self.inflow - self.outflow) / constraints["TANK_AREA"] 
        return dhdt 

    def update(self, dt):
        self.inflow = self.pump_pct * constraints["MAX_PUMP_FLOW"]

        self.outflow = (
            self.valve_pct
            * constraints["MAX_OUTFLOW"]
            * np.sqrt(self.level / constraints["MAX_LEVEL"])
        )

        dhdt = self.calculate_derivative()

        self.level += dhdt * dt

        self.level = np.clip(
            self.level,
            0.0,
            constraints["MAX_LEVEL"]
        )

    def set_pump(self, pump_pct):
        self.pump_pct = np.clip(pump_pct, 0.0, 1.0)

    def set_valve(self, valve_pct):
        self.valve_pct = np.clip(valve_pct, 0.0, 1.0)

    def get_state(self):
        return {
            "level": self.level,
            "inflow": self.inflow,
            "outflow": self.outflow,
            "pump_pct": self.pump_pct,
            "valve_pct": self.valve_pct,
        }

    
