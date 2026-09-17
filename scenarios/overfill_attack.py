"""
Scenario C: Overfill Attack.
Attacker exploits backend authorization bypass, commands pump 100% and valve 0%.
Expected result: Detector raises CRITICAL Overfill Trajectory Advisory.
"""

import time
from backend.api import BackendAPI
from control.command_gateway import CommandGateway
from mqtt.client import ICSCMQTTClient


def run_scenario() -> dict:
    mqtt_client = ICSCMQTTClient(client_id="scenario-overfill")
    mqtt_client.connect()
    time.sleep(0.5)

    gateway = CommandGateway(mqtt_client)
    api = BackendAPI(gateway)

    print("\n[SCENARIO C] Running Overfill Attack...")

    # 1. Attacker login as guest
    ok, _, auth = api.login("attacker_01", "guest")
    guest_token = auth["token"]

    # 2. Exploit backend authorization bypass
    api.submit_vulnerable_command(guest_token, "valve 0")
    time.sleep(1.0)
    api.submit_vulnerable_command(guest_token, "pump 100")
    time.sleep(2.0)

    mqtt_client.disconnect()
    print("[SCENARIO C] Completed.")
    return {"scenario": "OVERFILL", "status": "ATTACK_EXECUTED"}


if __name__ == "__main__":
    run_scenario()
