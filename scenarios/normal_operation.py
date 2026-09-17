"""
Scenario A: Normal Operation.
Executes standard operator login, pump and valve adjustments within safe limits.
Expected result: Nominal state, 0 false positives.
"""

import time
from backend.api import BackendAPI
from control.command_gateway import CommandGateway
from mqtt.client import ICSCMQTTClient


def run_scenario() -> dict:
    mqtt_client = ICSCMQTTClient(client_id="scenario-normal")
    mqtt_client.connect()
    time.sleep(0.5)

    gateway = CommandGateway(mqtt_client)
    api = BackendAPI(gateway)

    print("\n[SCENARIO A] Running Normal Operation...")

    # 1. Login as operator
    ok, _, auth = api.login("operator_01", "operator123")
    token = auth["token"]

    # 2. Legitimate control actions
    api.submit_command(token, "valve 40")
    time.sleep(1.0)
    api.submit_command(token, "pump 50")
    time.sleep(1.0)
    api.submit_command(token, "setpoint 0.5")
    time.sleep(1.0)

    mqtt_client.disconnect()
    print("[SCENARIO A] Completed.")
    return {"scenario": "NORMAL", "status": "SUCCESS"}


if __name__ == "__main__":
    run_scenario()
