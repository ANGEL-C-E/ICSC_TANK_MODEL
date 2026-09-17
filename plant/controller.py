"""
Plant State Machine & Simulation Loop Controller.

State Machine transitions:
    IDLE -> RUNNING -> WARNING -> FAULT -> EMERGENCY

Listens to MQTT commands on 'ics/control/commands' (and legacy 'plant/commands').
Publishes plant state to 'ics/plant/telemetry' and ACKs to 'ics/control/acknowledgements'.
Persists all state data to SQLite database.
"""

import json
import time
from typing import Any, Dict, Optional

import core.config as cfg
from core.database import db
from core.models import CommandACK, TelemetryMessage
from mqtt.client import ICSCMQTTClient
import mqtt.topics as topics
from plant.tank import TankProcess


class PlantOperatingState:
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    MAINTENANCE = "MAINTENANCE"
    WARNING = "WARNING"
    FAULT = "FAULT"
    EMERGENCY = "EMERGENCY"


class PlantController:
    def __init__(self, initial_level: float = 0.5):
        self.tank = TankProcess(initial_level=initial_level)
        self.operating_state = PlantOperatingState.RUNNING
        self.mqtt_client = ICSCMQTTClient(client_id="plant-controller")
        self._seq = 0
        self.sim_time = 0.0

    def start(self):
        # Subscribe to command topics
        self.mqtt_client.subscribe(topics.TOPIC_COMMANDS, self.on_command_received)
        self.mqtt_client.subscribe(topics.LEGACY_TOPIC_COMMANDS, self.on_command_received)
        self.mqtt_client.connect()
        print("[*] Plant Controller connected to MQTT bus and ready.")

    def stop(self):
        self.mqtt_client.disconnect()

    def on_command_received(self, topic: str, payload: Dict[str, Any]):
        cmd = payload.get("command") or payload.get("action")
        cmd_id = payload.get("command_id", f"cmd-{int(time.time()*1000)}")

        if not cmd:
            ack = CommandACK(command_id=cmd_id, status="rejected", reason="Missing command/action")
            self.mqtt_client.publish_json(topics.TOPIC_COMMAND_ACKS, ack.to_dict())
            return

        # Execute actuation in physics model
        if cmd == "pump":
            val = payload.get("value", 0.0)
            self.tank.pump.set_target(val)
            ack_status = "accepted"
        elif cmd == "valve":
            val = payload.get("value", 0.0)
            self.tank.valve.set_target(val)
            ack_status = "accepted"
        elif cmd == "setpoint":
            sp = payload.get("setpoint", 0.0)
            self.tank.setpoint = float(sp)
            ack_status = "accepted"
        elif cmd == "maintenance":
            mode_val = str(payload.get("mode", "on")).lower()
            if mode_val in ("on", "true", "start", "1"):
                self.operating_state = PlantOperatingState.MAINTENANCE
            else:
                self.operating_state = PlantOperatingState.RUNNING
            ack_status = "accepted"
        elif cmd == "estop":
            self.tank.pump.set_target(0.0)
            self.tank.valve.set_target(1.0)
            self.operating_state = PlantOperatingState.EMERGENCY
            ack_status = "accepted"
        elif cmd == "reset":
            self.operating_state = PlantOperatingState.RUNNING
            ack_status = "accepted"
        else:
            ack_status = "rejected"

        ack = CommandACK(command_id=cmd_id, status=ack_status)
        self.mqtt_client.publish_json(topics.TOPIC_COMMAND_ACKS, ack.to_dict())

    def update_state_machine(self, current_level: float, current_pressure: float):
        if self.operating_state in (PlantOperatingState.EMERGENCY, PlantOperatingState.MAINTENANCE):
            return

        if current_level >= cfg.MAX_SAFE_HEIGHT or current_level <= cfg.MIN_SAFE_HEIGHT:
            self.operating_state = PlantOperatingState.WARNING
        elif current_pressure >= cfg.MAX_SAFE_PRESSURE:
            self.operating_state = PlantOperatingState.FAULT
        else:
            self.operating_state = PlantOperatingState.RUNNING

    def step(self, dt: float = 0.1):
        self.tank.update(dt)
        self.sim_time += dt
        self._seq += 1

        state_dict = self.tank.get_measured_state()
        self.update_state_machine(state_dict["level"], state_dict["pressure"])

        telemetry = TelemetryMessage(
            ts=time.time(),
            seq=self._seq,
            level=state_dict["level"],
            pressure=state_dict["pressure"],
            pump_pct=state_dict["pump_pct"],
            valve_pct=state_dict["valve_pct"],
            inflow=state_dict["inflow"],
            outflow=state_dict["outflow"],
            operating_mode=self.operating_state,
        )

        t_dict = telemetry.to_dict()

        # Publish telemetry to new and legacy MQTT topics
        self.mqtt_client.publish_json(topics.TOPIC_TELEMETRY, t_dict)
        self.mqtt_client.publish_json(topics.LEGACY_TOPIC_TELEMETRY, t_dict)

        # Log telemetry history to SQLite database
        db.log_telemetry(t_dict, operating_mode=self.operating_state)

        return t_dict


def main():
    controller = PlantController(initial_level=0.5)
    controller.start()
    dt = 0.1
    print("[*] Plant controller physics loop starting (0.1s dt). Ctrl+C to stop.")
    try:
        step_count = 0
        while True:
            t_dict = controller.step(dt)
            step_count += 1
            if step_count % 100 == 0:
                print(
                    f"[t={controller.sim_time:6.1f}s] mode={t_dict['operating_mode']:7s} | "
                    f"level={t_dict['level']:6.3f}m | pressure={t_dict['pressure']/1000:5.2f}kPa | "
                    f"pump={t_dict['pump_pct']*100:5.1f}% | valve={t_dict['valve_pct']*100:5.1f}%"
                )
            time.sleep(dt)
    except KeyboardInterrupt:
        print("\n[*] Controller stopped.")
    finally:
        controller.stop()


if __name__ == "__main__":
    main()
