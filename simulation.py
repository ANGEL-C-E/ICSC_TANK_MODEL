from server import TankModel
from mqtt_client import MQTTClient
import time


tank = TankModel(level=4.0)

mqtt = MQTTClient()

mqtt.pump_callback = tank.set_pump
mqtt.valve_callback = tank.set_valve

mqtt.connect()

dt = 0.1
sim_time = 0.0

while True:
    tank.update(dt)
    sim_time += dt

    telemetry = {
        "time": sim_time,
        **tank.get_state()
    }

    mqtt.publish_telemetry(telemetry)

    time.sleep(dt)