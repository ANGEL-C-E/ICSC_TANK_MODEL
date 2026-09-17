"""
Command Detector evaluating static rules (Rule A, Rule B, Rule C).
"""

from typing import Any, Dict, List, Optional
import core.config as cfg


class CommandDetector:
    @staticmethod
    def evaluate_static_rules(cmd_type: str, val: Optional[float], h: float,
                              valve_pct: float, pump_pct: float) -> List[Dict[str, Any]]:
        alerts = []

        if cmd_type == "pump" and val is not None:
            turning_on = val > 1e-6
            # Rule A: Pump ON while outlet valve closed and tank level > 0.80 m
            if turning_on and valve_pct <= 1e-6 and h > cfg.RULE_A_HEIGHT:
                alerts.append({
                    "rule": "Rule A (Overfill Context)",
                    "severity": "CRITICAL",
                    "what": f"Pump ON commanded while outlet valve is 0% open and tank is at {h:.2f}m.",
                    "consequence": "Imminent tank overfill and pressure spike.",
                    "advice": "Open the outlet valve before energizing the pump.",
                    "confidence": 0.95
                })

            # Rule B: Pump OFF while valve 100% open and tank level < 0.10 m
            if not turning_on and valve_pct >= 0.99 and h < cfg.MIN_SAFE_HEIGHT:
                alerts.append({
                    "rule": "Rule B (Drainage Context)",
                    "severity": "WARNING",
                    "what": f"Pump OFF commanded with valve 100% open and tank nearly empty ({h:.2f}m).",
                    "consequence": "Tank will drain dry; downstream equipment may lose prime and run dry.",
                    "advice": "Close outlet valve or raise level before stopping pump.",
                    "confidence": 0.85
                })

        return alerts
