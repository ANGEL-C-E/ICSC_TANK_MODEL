"""
Temporal Detector analyzing telemetry timestamps, sequence continuity, and feed freshness.
"""

import time
from typing import Any, Dict, List, Optional
import core.config as cfg


class TemporalDetector:
    def __init__(self):
        self.last_seq: Optional[int] = None
        self.last_telemetry_time: float = time.time()

    def process_telemetry_temporal(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        anomalies = []
        now = time.time()
        seq = payload.get("seq")
        ts = payload.get("ts")

        # 1. Sequence checks
        if seq is not None and self.last_seq is not None:
            if seq <= self.last_seq:
                anomalies.append({
                    "type": "seq_replay",
                    "severity": "HIGH",
                    "msg": f"Sequence number repeated or went backwards ({self.last_seq} -> {seq})."
                })
            elif seq - self.last_seq > cfg.SEQUENCE_GAP_MAX:
                anomalies.append({
                    "type": "seq_gap",
                    "severity": "WARNING",
                    "msg": f"Gap of {seq - self.last_seq} sequence numbers detected."
                })

        # 2. Timestamp checks
        if ts is not None:
            if ts > now + cfg.REPLAY_TIME_TOLERANCE:
                anomalies.append({
                    "type": "future_timestamp",
                    "severity": "WARNING",
                    "msg": "Telemetry timestamp is in the future."
                })
            elif now - ts > cfg.REPLAY_TIME_TOLERANCE:
                anomalies.append({
                    "type": "stale_timestamp",
                    "severity": "WARNING",
                    "msg": f"Telemetry timestamp is {now - ts:.1f}s older than receipt time."
                })

        if seq is not None:
            self.last_seq = seq
        self.last_telemetry_time = now
        return anomalies

    def check_command_staleness(self) -> Optional[Dict[str, Any]]:
        now = time.time()
        age = now - self.last_telemetry_time
        if age > cfg.TELEMETRY_STALE_AFTER:
            return {
                "type": "stale_command_context",
                "severity": "WARNING",
                "msg": f"Command evaluated without fresh telemetry feedback (age {age:.1f}s)."
            }
        return None
