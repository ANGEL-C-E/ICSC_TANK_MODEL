"""
Scenario 7: Telemetry Replay Attack.
Attacker replays old telemetry frames to keep control room calm while tank level changes.
Expected: Detector flags residual divergence and stale timestamp advisory.
"""

import time
from mqtt.client import ICSCMQTTClient
import mqtt.topics as topics


def run_scenario() -> dict:
    mqtt_client = ICSCMQTTClient(client_id="scenario-telemetry-replay")
    mqtt_client.connect()
    time.sleep(0.5)

    print("\n[SCENARIO 7] Running Telemetry Replay Attack...")

    # Replay old telemetry sample from history with stale timestamp
    stale_telemetry = {
        "ts": time.time() - 45.0,
        "seq": 5,
        "level": 0.50,
        "pressure": 4905.0,
        "pump_pct": 0.0,
        "valve_pct": 0.5,
        "inflow": 0.0,
        "outflow": 0.044,
        "operating_mode": "RUNNING"
    }

    print("  -> Publishing replayed stale telemetry frame...")
    mqtt_client.publish_json(topics.TOPIC_TELEMETRY, stale_telemetry)
    time.sleep(1.0)

    mqtt_client.disconnect()
    print("[SCENARIO 7] Completed.")
    return {"scenario": "TELEMETRY_REPLAY", "status": "ATTACK_EXECUTED"}


if __name__ == "__main__":
    run_scenario()
