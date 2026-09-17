"""
Telemetry Collector storing recent samples in a thread-safe sliding buffer.
"""

from collections import deque
import threading
from typing import Any, Dict, List


class TelemetryCollector:
    def __init__(self, maxlen: int = 1000):
        self.buffer = deque(maxlen=maxlen)
        self.lock = threading.Lock()

    def add_sample(self, sample: Dict[str, Any]):
        with self.lock:
            self.buffer.append(sample)

    def get_latest(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.buffer[-1]) if self.buffer else {}

    def get_recent_samples(self, count: int = 50) -> List[Dict[str, Any]]:
        with self.lock:
            samples = list(self.buffer)
            return [dict(s) for s in samples[-count:]]
