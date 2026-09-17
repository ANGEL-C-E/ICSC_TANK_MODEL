"""
Telemetry Replay Engine for scenario testing replay and sequence gap attacks.
"""

import time
from typing import Any, Dict, List
import mqtt.topics as topics


class TelemetryReplayer:
    def __init__(self, mqtt_client):
        self.mqtt_client = mqtt_client
        self.recorded_samples: List[Dict[str, Any]] = []

    def record_sample(self, sample: Dict[str, Any]):
        self.recorded_samples.append(dict(sample))

    def replay_samples(self, modify_ts: bool = False, delay: float = 0.1):
        """Replay recorded samples over MQTT bus."""
        for sample in self.recorded_samples:
            s = dict(sample)
            if not modify_ts:
                # Keep original timestamp to trigger stale timestamp alert
                pass
            else:
                s["ts"] = time.time()
            self.mqtt_client.publish_json(topics.TOPIC_TELEMETRY, s)
            time.sleep(delay)
