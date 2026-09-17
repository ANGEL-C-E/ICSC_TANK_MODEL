"""
Scenario 2: Plant Startup & Shutdown.
Simulates graceful plant startup from IDLE to RUNNING, and controlled shutdown sequence.
"""

import time
from backend.api import BackendAPI
from control.command_gateway import CommandGateway
from mqtt.client import ICSCMQTTClient


def run_scenario() -> dict:
    mqtt_client = ICSCMQTTClient(client_id="scenario-startup-shutdown")
    mqtt_client.connect()
    time.sleep(0.5)

    gateway = CommandGateway(mqtt_client)
    api = BackendAPI(gateway)

    print("\n[SCENARIO 2] Running Plant Startup & Shutdown Sequence...")

    ok, _, auth = api.login("operator_01", "operator123")
    token = auth["token"]

    # 1. Startup sequence: Open outlet valve, start pump slowly, set setpoint
    print("  -> Executing Startup Sequence...")
    api.submit_command(token, "valve 60")
    time.sleep(0.5)
    api.submit_command(token, "pump 10")
    time.sleep(1.0)

    # 2. Shutdown sequence: Stop pump, close valve
    print("  -> Executing Graceful Shutdown Sequence...")
    api.submit_command(token, "pump 0")
    time.sleep(0.5)
    api.submit_command(token, "valve 0")
    time.sleep(1.0)

    mqtt_client.disconnect()
    print("[SCENARIO 2] Completed.")
    return {"scenario": "STARTUP_SHUTDOWN", "status": "SUCCESS"}


if __name__ == "__main__":
    run_scenario()
