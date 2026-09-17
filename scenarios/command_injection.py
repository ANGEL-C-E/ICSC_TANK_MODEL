"""
Scenario 4: Command Injection Attack.
Attacker exploits backend authorization bypass to submit unauthorized pump command.
Expected: Detector generates engineer advisory with uncertainty statement.
"""

import time
from backend.api import BackendAPI
from control.command_gateway import CommandGateway
from mqtt.client import ICSCMQTTClient


def run_scenario() -> dict:
    mqtt_client = ICSCMQTTClient(client_id="scenario-cmd-injection")
    mqtt_client.connect()
    time.sleep(0.5)

    gateway = CommandGateway(mqtt_client)
    api = BackendAPI(gateway)

    print("\n[SCENARIO 4] Running Command Injection Attack...")

    ok, _, auth = api.login("attacker_01", "guest")
    guest_token = auth["token"]

    print("  -> Injecting unauthorized pump command via vulnerable backend path...")
    api.submit_vulnerable_command(guest_token, "pump 100")
    time.sleep(1.0)

    mqtt_client.disconnect()
    print("[SCENARIO 4] Completed.")
    return {"scenario": "COMMAND_INJECTION", "status": "ATTACK_EXECUTED"}


if __name__ == "__main__":
    run_scenario()
