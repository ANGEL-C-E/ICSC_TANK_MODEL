"""
Scenario D: Dry-Run Attack.
Attacker commands valve 100% and pump 0% to drain tank completely.
Expected result: Detector raises WARNING Dry-Run Advisory.
"""

import time
from backend.api import BackendAPI
from control.command_gateway import CommandGateway
from mqtt.client import ICSCMQTTClient


def run_scenario() -> dict:
    mqtt_client = ICSCMQTTClient(client_id="scenario-dryrun")
    mqtt_client.connect()
    time.sleep(0.5)

    gateway = CommandGateway(mqtt_client)
    api = BackendAPI(gateway)

    print("\n[SCENARIO D] Running Dry-Run Attack...")

    ok, _, auth = api.login("attacker_01", "guest")
    guest_token = auth["token"]

    api.submit_vulnerable_command(guest_token, "pump 0")
    time.sleep(0.5)
    api.submit_vulnerable_command(guest_token, "valve 100")
    time.sleep(2.0)

    mqtt_client.disconnect()
    print("[SCENARIO D] Completed.")
    return {"scenario": "DRY_RUN", "status": "ATTACK_EXECUTED"}


if __name__ == "__main__":
    run_scenario()
