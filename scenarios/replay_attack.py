"""
Scenario F: Telemetry Replay Attack.
Injects old telemetry frames with stale timestamps and repeated sequence numbers.
Expected result: Detector raises HIGH Telemetry Replay / Residual Divergence Advisory.
"""

import time
from mqtt.client import ICSCMQTTClient
import mqtt.topics as topics


def run_scenario() -> dict:
    mqtt_client = ICSCMQTTClient(client_id="scenario-replay")
    mqtt_client.connect()
    time.sleep(0.5)

    print("\n[SCENARIO F] Running Telemetry Replay Attack...")

    # Stale telemetry frame from 30 seconds ago
    stale_frame = {
        "ts": time.time() - 30.0,
        "seq": 10,
        "level": 0.20,
        "pressure": 1962.0,
        "pump_pct": 1.0,
        "valve_pct": 0.0,
        "inflow": 0.5,
        "outflow": 0.0,
        "operating_mode": "RUNNING"
    }

    mqtt_client.publish_json(topics.TOPIC_TELEMETRY, stale_frame)
    time.sleep(1.0)

    mqtt_client.disconnect()
    print("[SCENARIO F] Completed.")
    return {"scenario": "TELEMETRY_REPLAY", "status": "ATTACK_EXECUTED"}


if __name__ == "__main__":
    run_scenario()
