"""
Interactive Operator Control Terminal CLI (`python -m cli.operator`).
Provides authenticated, role-gated plant control interface.
"""

import getpass
import json
import sys
import threading
import time
from typing import Any, Dict

from backend.api import BackendAPI
from control.command_gateway import CommandGateway
import core.config as cfg
from core.database import db
from mqtt.client import ICSCMQTTClient
import mqtt.topics as topics

latest_telemetry: Dict[str, Any] = {}
telemetry_lock = threading.Lock()


def on_telemetry(topic: str, payload: Dict[str, Any]):
    global latest_telemetry
    with telemetry_lock:
        latest_telemetry = payload


def print_status():
    with telemetry_lock:
        t = dict(latest_telemetry)
    if not t:
        print("[*] No telemetry received yet. Is the plant controller running?")
        return
    age = max(0.0, time.time() - t.get("ts", time.time()))
    print(
        f"Level:       {t.get('level', 0.0):.3f} m\n"
        f"Pressure:    {t.get('pressure', 0.0)/1000:.2f} kPa\n"
        f"Pump:        {t.get('pump_pct', 0.0)*100:.1f} %\n"
        f"Valve:       {t.get('valve_pct', 0.0)*100:.1f} %\n"
        f"Inflow:      {t.get('inflow', 0.0):.3f} m^3/s\n"
        f"Outflow:     {t.get('outflow', 0.0):.3f} m^3/s\n"
        f"Mode:        {t.get('operating_mode', 'UNKNOWN')}\n"
        f"Age:         {age:.1f} s"
    )


HELP_TEXT = """Available commands:
  pump <0-100>    Set pump power %
  valve <0-100>   Set valve opening %
  setpoint <m>    Request level setpoint
  estop           Emergency stop (Pump 0%, Valve 100%)
  reset           Reset fault/emergency state
  status          Show live plant telemetry
  telemetry       Show recent telemetry logs from SQLite
  alarms          Show recent security alerts from SQLite
  help            Show this help message
  logout / quit   Exit terminal"""


def main():
    mqtt_client = ICSCMQTTClient(client_id="operator-cli")
    mqtt_client.subscribe(topics.TOPIC_TELEMETRY, on_telemetry)
    mqtt_client.subscribe(topics.LEGACY_TOPIC_TELEMETRY, on_telemetry)
    mqtt_client.connect()

    gateway = CommandGateway(mqtt_client)
    api = BackendAPI(gateway)

    print("╔════════════════════════════════════════════╗")
    print("║          ICSC TANK CONTROL TERMINAL        ║")
    print("╚════════════════════════════════════════════╝\n")

    username = input("Username: ").strip()
    password = getpass.getpass("Password: ").strip()

    ok, msg, auth_res = api.login(username, password)
    if not ok:
        print(f"[!] {msg}")
        mqtt_client.disconnect()
        sys.exit(1)

    token = auth_res["token"]
    role = auth_res["role"]

    print(f"\n[*] Authentication successful.")
    print(f"[*] User: {username} | Role: {role} | Session: {token[:12]}...")
    print("[*] Type `help` for command list.\n")

    try:
        while True:
            line = input("plant> ").strip()
            if not line:
                continue
            cmd_name = line.split()[0].lower()

            if cmd_name in ("quit", "exit", "logout"):
                print("[*] Logging out...")
                break
            if cmd_name == "help":
                print(HELP_TEXT)
                continue
            if cmd_name == "status":
                print_status()
                continue
            if cmd_name == "telemetry":
                rows = db.get_recent_telemetry(limit=5)
                for r in reversed(rows):
                    print(f"  [seq={r['seq']}] level={r['level']:.3f}m | P={r['pressure']/1000:.2f}kPa | pump={r['pump_pct']*100:.0f}% | valve={r['valve_pct']*100:.0f}%")
                continue
            if cmd_name == "alarms":
                alerts = db.get_recent_alerts(limit=5)
                for a in reversed(alerts):
                    print(f"  [{a['severity']}] (score {a['anomaly_score']:.2f}) {a['what_happened']}")
                continue

            # Submit command through Command Gateway API
            ok, response_msg, res_dict = api.submit_command(token, line)
            if ok:
                print(f"[>] {response_msg}")
            else:
                print(f"[!] {response_msg}")

    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        mqtt_client.disconnect()
        print("[*] Terminal closed.")


if __name__ == "__main__":
    main()
