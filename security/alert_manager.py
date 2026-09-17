"""
Alert Manager & Anomaly Scoring Engine.

Computes weighted normalized anomaly score S_t in [0.0, 1.0].
Manages alert formatting, cooldowns, and SQLite alert logging.
"""

import json
import time
from typing import Any, Dict, Optional
import core.config as cfg
from core.database import db


class Alert:
    def __init__(self, severity: str, layer: str, what_happened: str, consequence: str,
                 advice: str, confidence: float, anomaly_score: float = 0.0,
                 equipment: str = "TANK-01", uncertainty_statement: str = "",
                 context: Optional[Dict[str, Any]] = None):
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.unix_ts = time.time()
        self.device_id = cfg.DEVICE_ID
        self.equipment = equipment
        self.severity = severity
        self.layer = layer
        self.what_happened = what_happened
        self.consequence = consequence
        self.advice = advice
        self.confidence = confidence
        self.anomaly_score = anomaly_score
        self.uncertainty_statement = uncertainty_statement or (
            f"Confidence: {confidence*100:.0f}%. Potential model deviation or uncalibrated sensor noise. Verify physical site gauges before intervention."
            if confidence < 0.90 else f"High Confidence ({confidence*100:.0f}%). Physical rule breach confirmed."
        )
        self.context = context or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "unix_ts": self.unix_ts,
            "device_id": self.device_id,
            "equipment": self.equipment,
            "severity": self.severity,
            "layer": self.layer,
            "what_happened": self.what_happened,
            "anomaly_score": round(self.anomaly_score, 3),
            "physical_context": self.context,
            "predicted_consequence": self.consequence,
            "confidence": self.confidence,
            "uncertainty_statement": self.uncertainty_statement,
            "action_advice": self.advice,
        }

    def render(self) -> str:
        bar = "=" * 64
        ctx_str = " | ".join(f"{k}: {v}" for k, v in self.context.items()) if self.context else "n/a"
        return (
            f"\n{bar}\n"
            f"[ENGINEER SECURITY ADVISORY - {self.severity}]\n"
            f"Equipment:   {self.equipment} ({self.device_id})\n"
            f"What:        {self.what_happened}\n"
            f"Why Matters: {self.consequence}\n"
            f"Context:     {ctx_str}\n"
            f"Advice:      {self.advice}\n"
            f"Uncertainty: {self.uncertainty_statement}\n"
            f"System Role: ADVISORY ONLY — Human Engineer decides action.\n"
            f"{bar}\n"
        )


class AlertManager:
    def __init__(self):
        self._cooldowns: Dict[str, float] = {}

    def calculate_anomaly_score(self, s_physics: float = 0.0, s_temporal: float = 0.0,
                                s_command: float = 0.0, s_sensor: float = 0.0,
                                s_trajectory: float = 0.0) -> float:
        """
        S_t = w1*S_phys + w2*S_temp + w3*S_cmd + w4*S_sens + w5*S_traj
        """
        score = (
            cfg.WEIGHT_PHYSICS * min(1.0, max(0.0, s_physics)) +
            cfg.WEIGHT_TEMPORAL * min(1.0, max(0.0, s_temporal)) +
            cfg.WEIGHT_COMMAND * min(1.0, max(0.0, s_command)) +
            cfg.WEIGHT_SENSOR * min(1.0, max(0.0, s_sensor)) +
            cfg.WEIGHT_TRAJECTORY * min(1.0, max(0.0, s_trajectory))
        )
        return min(1.0, max(0.0, float(score)))

    def emit_alert(self, key: str, severity: str, layer: str, what: str,
                   consequence: str, advice: str, confidence: float,
                   anomaly_score: float, equipment: str = "TANK-01",
                   uncertainty_statement: str = "",
                   context: Optional[Dict[str, Any]] = None) -> Optional[Alert]:
        now = time.time()
        last = self._cooldowns.get(key)
        if last is not None and now - last < cfg.ALERT_COOLDOWN:
            return None

        self._cooldowns[key] = now
        alert = Alert(
            severity=severity,
            layer=layer,
            what_happened=what,
            consequence=consequence,
            advice=advice,
            confidence=confidence,
            anomaly_score=anomaly_score,
            equipment=equipment,
            uncertainty_statement=uncertainty_statement,
            context=context
        )

        # Log alert into SQLite database
        db.log_alert(alert.to_dict())

        return alert
