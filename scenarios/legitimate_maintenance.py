"""
Scenario 3: Legitimate Maintenance Activity.
Engineer logs in, enables MAINTENANCE mode, strokes valve 0% -> 100%, tests pump cycling.
Expected: 0 false alarms during routine maintenance testing.
"""

import time
from backend.api import BackendAPI
from control.command_gateway import CommandGateway
from mqtt.client import ICSCMQTTClient


def run_scenario() -> dict:
    mqtt_client = ICSCMQTTClient(client_id="scenario-maintenance")
    mqtt_client.connect()
    time.sleep(0.5)

    gateway = CommandGateway(mqtt_client)
    api = BackendAPI(gateway)

    print("\n[SCENARIO 3] Running Legitimate Maintenance Testing...")

    # 1. Login as engineer
    ok, _, auth = api.login("engineer_01", "engineer123")
    token = auth["token"]

    # 2. Switch plant to MAINTENANCE mode
    print("  -> Enabling MAINTENANCE Mode...")
    api.submit_command(token, "maintenance on")
    time.sleep(0.5)

    # 3. Perform maintenance maneuvers (valve stroking, pump testing)
    print("  -> Performing valve stroke test (0% -> 100%)...")
    api.submit_command(token, "valve 0")
    time.sleep(0.5)
    api.submit_command(token, "valve 100")
    time.sleep(0.5)

    print("  -> Performing pump bump test...")
    api.submit_command(token, "pump 50")
    time.sleep(0.5)
    api.submit_command(token, "pump 0")
    time.sleep(0.5)

    # 4. Exit MAINTENANCE mode
    print("  -> Exiting MAINTENANCE Mode back to RUNNING...")
    api.submit_command(token, "maintenance off")
    time.sleep(0.5)

    mqtt_client.disconnect()
    print("[SCENARIO 3] Completed.")
    return {"scenario": "LEGITIMATE_MAINTENANCE", "status": "SUCCESS"}


if __name__ == "__main__":
    run_scenario()
