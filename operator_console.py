"""
Interactive operator console for the ICSC plant.

Publishes JSON commands on plant/commands, exactly as the detector expects
them, and prints advisory alerts coming back on plant/alerts.

Commands:
    pump <0-100>     Set pump power in percent        (e.g. `pump 80`)
    valve <0-100>    Set valve opening in percent     (e.g. `valve 25`)
    setpoint <m>     Request a level setpoint         (e.g. `setpoint 0.7`)
    status           Show current state from telemetry
    on / off         Pump fully on / off
    open / close     Valve fully open / closed
    quit             Exit

Requires the simulation to be running so telemetry feeds the state display.
"""

import json
import threading

import config as cfg
from mqtt_common import connect, make_client

latest_state = {}
state_lock = threading.Lock()


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[*] Operator console connected to broker (code: {rc})")
    client.subscribe(cfg.TOPIC_ALERTS)
    client.subscribe(cfg.TOPIC_TELEMETRY)
    print("[*] Watching alerts and telemetry. Type `help` for commands.\n")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except ValueError:
        return

    if msg.topic == cfg.TOPIC_ALERTS:
        sev = payload.get("severity", "?")
        print(f"\n[SECURITY ADVISORY - {sev}] {payload.get('what_happened', '')}")
        print(f"    Consequence: {payload.get('predicted_consequence', '')}")
        print(f"    Advice:      {payload.get('action_advice', '')}")
        print("operator> ", end="", flush=True)
    elif msg.topic == cfg.TOPIC_TELEMETRY:
        with state_lock:
            global latest_state
            latest_state = payload


def print_status():
    with state_lock:
        s = dict(latest_state)
    if not s:
        print("[*] No telemetry received yet. Is the simulation running?")
        return
    age = max(0.0, __import__("time").time() - s.get("ts", 0))
    print(
        f"level {s.get('level', 0):.3f} m | pressure {s.get('pressure', 0) / 1000:.2f} kPa | "
        f"pump {s.get('pump_pct', 0) * 100:.0f}% | valve {s.get('valve_pct', 0) * 100:.0f}% | "
        f"in {s.get('inflow', 0):.3f} m^3/s | out {s.get('outflow', 0):.3f} m^3/s | "
        f"telemetry age {age:.1f}s"
    )


def build_command(tokens):
    """Turn CLI tokens into a JSON command payload, or None."""
    if not tokens:
        return None
    cmd = tokens[0].lower()

    if cmd in ("on", "off"):
        return {"action": "pump", "value": 1.0 if cmd == "on" else 0.0,
                "label": "PUMP_ON" if cmd == "on" else "PUMP_OFF"}
    if cmd in ("open", "close"):
        return {"action": "valve", "value": 1.0 if cmd == "open" else 0.0}
    if cmd == "pump" and len(tokens) >= 2:
        return {"action": "pump", "value": max(0.0, min(100.0, float(tokens[1]))) / 100.0}
    if cmd == "valve" and len(tokens) >= 2:
        return {"action": "valve", "value": max(0.0, min(100.0, float(tokens[1]))) / 100.0}
    if cmd == "setpoint" and len(tokens) >= 2:
        return {"action": "setpoint", "setpoint": float(tokens[1])}
    return None


HELP = """Commands:
  pump <0-100>    Set pump power %         on / off      Pump fully on/off
  valve <0-100>   Set valve opening %      open / close  Valve fully open/closed
  setpoint <m>    Request level setpoint   status        Show plant state
  quit            Exit"""


def main():
    client = make_client(on_connect, on_message)
    connect(client)
    client.loop_start()

    print("[*] ICSC operator console (advisories appear as they fire).")
    print(HELP)
    try:
        while True:
            line = input("operator> ").strip()
            if not line:
                continue
            tokens = line.split()
            cmd = tokens[0].lower()

            if cmd in ("quit", "exit", "q"):
                break
            if cmd == "help":
                print(HELP)
                continue
            if cmd == "status":
                print_status()
                continue

            payload = build_command(tokens)
            if payload is None:
                print("[!] Unknown command. Type `help`.")
                continue

            client.publish(cfg.TOPIC_COMMANDS, json.dumps(payload))
            print(f"[>] Sent: {json.dumps(payload)}")
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        client.loop_stop()
        client.disconnect()
        print("[*] Operator console closed.")


if __name__ == "__main__":
    main()
