"""
Scenario 1: Normal Running.
Simulates standard steady-state operational profile.
Expected: 0 false alarms.
"""

import time
from backend.api import BackendAPI
from control.command_gateway import CommandGateway
from mqtt.client import ICSCMQTTClient


def run_scenario() -> dict:
    mqtt_client = ICSCMQTTClient(client_id="scenario-normal-running")
    mqtt_client.connect()
    time.sleep(0.5)

    gateway = CommandGateway(mqtt_client)
    api = BackendAPI(gateway)

    print("\n[SCENARIO 1] Running Normal Steady-State Operation...")

    ok, _, auth = api.login("operator_01", "operator123")
    token = auth["token"]

    api.submit_command(token, "valve 50")
    time.sleep(0.5)
    api.submit_command(token, "pump 10")
    time.sleep(1.0)
    api.submit_command(token, "setpoint 0.5")
    time.sleep(1.0)

    mqtt_client.disconnect()
    print("[SCENARIO 1] Completed.")
    return {"scenario": "NORMAL_RUNNING", "status": "SUCCESS"}


if __name__ == "__main__":
    run_scenario()
