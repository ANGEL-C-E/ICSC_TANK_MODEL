"""
ICSC plant simulation entry point.

Runs the TankModel in real time, publishes telemetry over MQTT, and applies
commands received from operators. Ctrl+C for a clean shutdown.

Requires an MQTT broker on localhost:1883 (e.g. `mosquitto -v`).
Run the detector in a second terminal:  python detector.py
Drive the plant from a third:           python operator_console.py
"""

import time

from mqtt_client import MQTTClient
from server import TankModel


def main():
    tank = TankModel(level=0.5)
    mqtt = MQTTClient()

    mqtt.pump_callback = tank.set_pump
    mqtt.valve_callback = tank.set_valve
    mqtt.setpoint_callback = tank.set_setpoint

    mqtt.connect()

    dt = 0.1
    sim_time = 0.0
    report_every = 100  # console status every 100 steps (10 s)

    print("[*] Plant simulation running. Ctrl+C to stop.")
    try:
        while True:
            tank.update(dt)
            sim_time += dt

            mqtt.publish_telemetry(tank)

            step = int(sim_time / dt)
            if step % report_every == 0:
                state = tank.get_state()
                sp = f" | setpoint {tank.setpoint:.2f} m" if tank.setpoint is not None else ""
                print(
                    f"[t={sim_time:7.1f}s] level {state['level']:6.3f} m | "
                    f"pump {state['pump_pct'] * 100:5.1f}% | "
                    f"valve {state['valve_pct'] * 100:5.1f}% | "
                    f"in {state['inflow']:.3f} | out {state['outflow']:.3f}{sp}"
                )

            time.sleep(dt)
    except KeyboardInterrupt:
        print(f"\n[*] Simulation stopped at t={sim_time:.1f}s, "
              f"level {tank.level:.3f} m.")
    finally:
        mqtt.disconnect()


if __name__ == "__main__":
    main()
