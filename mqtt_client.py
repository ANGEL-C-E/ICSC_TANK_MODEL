"""
MQTT bridge between the plant bus and the TankModel.

Subscribes to JSON commands on plant/commands and applies them to the tank;
publishes the tank state as JSON telemetry on plant/telemetry every step.

Telemetry payload:
    {"ts": <unix seconds>, "seq": <int>, "level": <m>, "inflow": <m^3/s>,
     "outflow": <m^3/s>, "pump_pct": 0..1, "valve_pct": 0..1,
     "pressure": <Pa>}

Command payloads (JSON):
    {"action": "pump",     "value": 0..1, "label": "PUMP_ON"}   # label optional
    {"action": "valve",    "value": 0..1}
    {"action": "setpoint", "setpoint": <meters>}

Backward compatibility: bare float payloads on the command topic
(e.g. "0.8") are still accepted, but a WARNING is printed recommending the
JSON schema (bare floats carry no operator identity).
"""

import json
import time

import config as cfg
from mqtt_common import connect, make_client


class MQTTClient:
    def __init__(self, broker=cfg.BROKER, port=cfg.PORT):
        self.broker = broker
        self.port = port

        self.pump_callback = None    # fn(value: 0..1)
        self.valve_callback = None   # fn(value: 0..1)
        self.setpoint_callback = None  # fn(setpoint: meters)

        self.client = make_client(self.on_connect, self.on_message)

        self._seq = 0

    def connect(self):
        connect(self.client, self.broker, self.port)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    # ------------------------------------------------------------------
    # Incoming commands
    # ------------------------------------------------------------------
    def on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"[*] Simulation connected to broker (code: {rc})")
        client.subscribe(cfg.TOPIC_COMMANDS)
        print(f"[*] Subscribed to commands: {cfg.TOPIC_COMMANDS}")

    def on_message(self, client, userdata, msg):
        raw = msg.payload.decode(errors="replace").strip()
        try:
            payload = json.loads(raw)
        except ValueError:
            # Legacy compatibility: bare float like "0.8" or "80"
            try:
                value = float(raw)
            except ValueError:
                print(f"[!] Invalid command payload: {raw!r}")
                return
            self._dispatch_command(
                {"action": self._guess_action(msg.topic), "value": value},
                legacy=True)
            return

        self._dispatch_command(payload)

    @staticmethod
    def _guess_action(topic):
        """Legacy single-topic mode: infer action from the topic name."""
        if "pump" in topic:
            return "pump"
        if "valve" in topic:
            return "valve"
        return "pump"

    def _dispatch_command(self, payload, legacy=False):
        if not isinstance(payload, dict):
            print(f"[!] Invalid command payload: {payload!r}")
            return

        action = payload.get("action")
        value = payload.get("value")
        label = payload.get("label", "")

        if action == "pump":
            if not isinstance(value, (int, float)):
                print(f"[!] Pump command requires numeric 'value': {payload!r}")
                return
            print(f"[*] Pump command: {value:.2f}"
                  + (f" ({label})" if label else "")
                  + (" [legacy float payload]" if legacy else ""))
            if self.pump_callback:
                self.pump_callback(value)

        elif action == "valve":
            if not isinstance(value, (int, float)):
                print(f"[!] Valve command requires numeric 'value': {payload!r}")
                return
            print(f"[*] Valve command: {value:.2f}"
                  + (" [legacy float payload]" if legacy else ""))
            if self.valve_callback:
                self.valve_callback(value)

        elif action == "setpoint":
            sp = payload.get("setpoint")
            if not isinstance(sp, (int, float)):
                print(f"[!] Setpoint command requires numeric 'setpoint': {payload!r}")
                return
            print(f"[*] Setpoint command: {sp:.2f} m")
            if self.setpoint_callback:
                self.setpoint_callback(sp)

        else:
            print(f"[!] Unknown command action: {payload!r}")

    # ------------------------------------------------------------------
    # Outgoing telemetry
    # ------------------------------------------------------------------
    def publish_telemetry(self, tank):
        """Publish the current TankModel state as a telemetry message."""
        state = tank.get_state()
        self._seq += 1
        telemetry = {
            "ts": time.time(),
            "seq": self._seq,
            "level": round(state["level"], 6),
            "inflow": round(state["inflow"], 6),
            "outflow": round(state["outflow"], 6),
            "pump_pct": round(state["pump_pct"], 6),
            "valve_pct": round(state["valve_pct"], 6),
            "pressure": round(cfg.RHO * cfg.G * state["level"], 3),
        }
        self.client.publish(cfg.TOPIC_TELEMETRY, json.dumps(telemetry))
        return telemetry
