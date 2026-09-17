"""
Scenario E: Oscillation Attack.
Attacker rapidly toggles pump between 0% and 100% to cause mechanical hunting.
Expected result: Detector raises HIGH Behavioral Command Oscillation Advisory.
"""

import time
from backend.api import BackendAPI
from control.command_gateway import CommandGateway
from mqtt.client import ICSCMQTTClient


def run_scenario() -> dict:
    mqtt_client = ICSCMQTTClient(client_id="scenario-oscillation")
    mqtt_client.connect()
    time.sleep(0.5)

    gateway = CommandGateway(mqtt_client)
    api = BackendAPI(gateway)

    print("\n[SCENARIO E] Running Oscillation Attack...")

    ok, _, auth = api.login("attacker_01", "guest")
    guest_token = auth["token"]

    for _ in range(6):
        api.submit_vulnerable_command(guest_token, "pump 100")
        time.sleep(0.2)
        api.submit_vulnerable_command(guest_token, "pump 0")
        time.sleep(0.2)

    mqtt_client.disconnect()
    print("[SCENARIO E] Completed.")
    return {"scenario": "OSCILLATION", "status": "ATTACK_EXECUTED"}


if __name__ == "__main__":
    run_scenario()
