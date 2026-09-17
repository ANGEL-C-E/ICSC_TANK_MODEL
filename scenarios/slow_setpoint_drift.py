"""
Scenario 6: Slow Setpoint Drift Attack.
Attacker slowly moves setpoint in small increments (+0.10m step changes) to shift safe operating limits.
Expected: Detector tracks cumulative setpoint drift and raises HIGH Advisory.
"""

import time
from backend.api import BackendAPI
from control.command_gateway import CommandGateway
from mqtt.client import ICSCMQTTClient


def run_scenario() -> dict:
    mqtt_client = ICSCMQTTClient(client_id="scenario-setpoint-drift")
    mqtt_client.connect()
    time.sleep(0.5)

    gateway = CommandGateway(mqtt_client)
    api = BackendAPI(gateway)

    print("\n[SCENARIO 6] Running Slow Setpoint Drift Attack...")

    ok, _, auth = api.login("attacker_01", "guest")
    guest_token = auth["token"]

    for sp in (0.4, 0.5, 0.65, 0.80):
        print(f"  -> Drifting setpoint to {sp:.2f}m...")
        api.submit_vulnerable_command(guest_token, f"setpoint {sp}")
        time.sleep(0.3)

    mqtt_client.disconnect()
    print("[SCENARIO 6] Completed.")
    return {"scenario": "SLOW_SETPOINT_DRIFT", "status": "ATTACK_EXECUTED"}


if __name__ == "__main__":
    run_scenario()
