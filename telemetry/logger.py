"""
Telemetry Logger persisting live telemetry to SQLite database.
"""

from typing import Any, Dict
from core.database import db


class TelemetryLogger:
    @staticmethod
    def log_telemetry(payload: Dict[str, Any], operating_mode: str = "RUNNING"):
        db.log_telemetry(payload, operating_mode=operating_mode)
