"""
Scenario 5: Wrong-Moment Attack (Pump ON against Closed Valve).
Attacker issues a valid pump 100% command at the wrong moment while outlet valve is 0% open.
Expected: Detector raises CRITICAL Rule A Rule Advisory with Equipment Tag & Uncertainty Statement.
"""

import time
from backend.api import BackendAPI
from control.command_gateway import CommandGateway
from mqtt.client import ICSCMQTTClient


def run_scenario() -> dict:
    mqtt_client = ICSCMQTTClient(client_id="scenario-wrong-moment")
    mqtt_client.connect()
    time.sleep(0.5)

    gateway = CommandGateway(mqtt_client)
    api = BackendAPI(gateway)

    print("\n[SCENARIO 5] Running Wrong-Moment Attack (Pump ON vs Closed Valve)...")

    ok, _, auth = api.login("attacker_01", "guest")
    guest_token = auth["token"]

    print("  -> Closing valve V-101 (0%)...")
    api.submit_vulnerable_command(guest_token, "valve 0")
    time.sleep(0.5)

    print("  -> Switched pump P-101 ON (100%) at wrong moment...")
    api.submit_vulnerable_command(guest_token, "pump 100")
    time.sleep(1.0)

    mqtt_client.disconnect()
    print("[SCENARIO 5] Completed.")
    return {"scenario": "WRONG_MOMENT_ATTACK", "status": "ATTACK_EXECUTED"}


if __name__ == "__main__":
    run_scenario()
