#code to run the simulation and watch data telemetry

from server import TankModel 


tank = TankModel(
    level=4.0,
)

tank.set_pump(pump_pct=1.0)
tank.set_valve(valve_pct=0.0)

history = []
step = 10

for t in range(step):
    tank.update(dt=0.01)
    
    history.append(
        {
        "time": t * 0.1,
        **tank.get_state()
    }
)

print(history)