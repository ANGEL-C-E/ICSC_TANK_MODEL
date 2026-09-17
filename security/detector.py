"""
Process-aware anomaly detector for the ICSC tank plant.

Passively monitors the MQTT bus, running incoming telemetry and control commands
through a 4-layer inspection pipeline. Operates purely out-of-band as an ADVISORY monitor.
"""

import json
import math
import time
from typing import Any, Dict, List, Optional

import core.config as cfg
from mqtt.client import ICSCMQTTClient
import mqtt.topics as topics
from security.alert_manager import Alert, AlertManager
from security.behavioral_detector import BehavioralDetector
from security.command_detector import CommandDetector
from security.physics_detector import PhysicsDetector
from security.temporal_detector import TemporalDetector


class AnomalyDetector:
    def __init__(self):
        self.physics = PhysicsDetector()
        self.temporal = TemporalDetector()
        self.behavior = BehavioralDetector()
        self.command = CommandDetector()
        self.alert_mgr = AlertManager()

        self.current_state = {
            "h": 0.5,
            "pressure": cfg.RHO * cfg.G * 0.5,
            "pump": 0.0,
            "valve": 0.0,
        }
        self.last_ts = time.time()

    def process_telemetry(self, payload: Dict[str, Any]) -> List[Alert]:
        alerts = []
        now = time.time()

        # 1. Temporal checks
        temp_anomalies = self.temporal.process_telemetry_temporal(payload)
        s_temporal = 0.8 if temp_anomalies else 0.0

        h = float(payload.get("level", self.current_state["h"]))
        pump = float(payload.get("pump_pct", self.current_state["pump"]))
        valve = float(payload.get("valve_pct", self.current_state["valve"]))
        pressure = float(payload.get("pressure", cfg.RHO * cfg.G * h))

        dt = max(0.01, min(1.0, now - self.last_ts))
        self.last_ts = now

        # 2. Physics Residual Analysis
        pred_h, residual = self.physics.compute_residual(h, pump, valve, dt)
        s_physics = min(1.0, residual / (5.0 * cfg.REPLAY_TOLERANCE))

        if residual > cfg.REPLAY_TOLERANCE:
            score = self.alert_mgr.calculate_anomaly_score(s_physics=s_physics, s_temporal=s_temporal)
            alert = self.alert_mgr.emit_alert(
                key="residual_divergence",
                severity="HIGH",
                layer="3. Physics Model Residual",
                what=f"Reported level {h:.3f}m deviates {residual:.3f}m from shadow physics prediction ({pred_h:.3f}m).",
                consequence="Telemetry spoofing, sensor bias, or unmodeled physical leakage.",
                advice="Cross-check level sensor readings against secondary pressure transducer.",
                confidence=0.85,
                anomaly_score=score,
                context={"level": h, "predicted": pred_h, "residual": residual}
            )
            if alert:
                alerts.append(alert)

        # 3. Behavioral checks
        beh_anomaly = self.behavior.process_telemetry_behavior(h, pump)
        if beh_anomaly:
            score = self.alert_mgr.calculate_anomaly_score(s_temporal=0.6)
            alert = self.alert_mgr.emit_alert(
                key="frozen_feed",
                severity=beh_anomaly["severity"],
                layer="4. Temporal & Behavioral",
                what=beh_anomaly["msg"],
                consequence="Sensor failure, frozen feed, or telemetry replay.",
                advice="Verify physical telemetry stream and transducer wiring.",
                confidence=0.80,
                anomaly_score=score,
                context={"level": h, "pump_pct": pump}
            )
            if alert:
                alerts.append(alert)

        # Check operating mode for maintenance suppression
        operating_mode = payload.get("operating_mode", self.current_state.get("mode", "RUNNING"))
        is_maintenance = (operating_mode == "MAINTENANCE")

        # 4. Pressure sanity check (Rule C)
        if pressure > cfg.MAX_SAFE_PRESSURE and not is_maintenance:
            score = self.alert_mgr.calculate_anomaly_score(s_physics=0.9)
            alert = self.alert_mgr.emit_alert(
                key="pressure_limit",
                severity="CRITICAL",
                layer="2. Static Rule (C: Pressure Limit)",
                what=f"Hydrostatic pressure {pressure/1000:.2f}kPa exceeds safe limit ({cfg.MAX_SAFE_PRESSURE/1000:.2f}kPa).",
                consequence="Imminent over-pressure risk to physical tank vessel.",
                advice="Open outlet valve V-101 immediately or de-energize pump P-101.",
                confidence=0.95,
                anomaly_score=score,
                equipment="TANK-01 / PRESSURE-SENSOR-01",
                uncertainty_statement="High Confidence (95%). Physical hydrostatic pressure limit exceeded.",
                context={"pressure_kpa": pressure / 1000, "level": h}
            )
            if alert:
                alerts.append(alert)

        # Update cached state
        self.current_state = {"h": h, "pressure": pressure, "pump": pump, "valve": valve, "mode": operating_mode}
        return alerts

    def evaluate_command_pre_actuation(self, payload: Dict[str, Any], plant_state: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, List[Alert]]:
        """
        Evaluates a command pre-actuation against physical process boundaries.
        Returns (is_blocked, block_reason, alerts).
        Under ADVISORY mode (default), returns is_blocked = False to enforce human-in-the-loop decision principle.
        """
        alerts = self.process_command(payload)

        # In ADVISORY mode (core project requirement), NEVER block actuation automatically.
        if cfg.SECURITY_MODE != "ACTIVE":
            return False, "", alerts

        # ACTIVE IPS mode (optional override)
        state = plant_state or self.current_state
        h = state.get("h", self.current_state["h"])
        pressure = state.get("pressure", self.current_state["pressure"])
        valve = state.get("valve", self.current_state["valve"])
        cmd_name = payload.get("command") or payload.get("action")
        val = payload.get("value")

        if cmd_name == "pump" and val is not None and val > 1e-6:
            if pressure >= cfg.MAX_SAFE_PRESSURE or h >= cfg.MAX_SAFE_HEIGHT:
                return True, f"Tank level ({h:.2f}m) or pressure ({pressure/1000:.2f}kPa) exceeds safe bounds.", alerts
            if valve <= 1e-6 and h > cfg.RULE_A_HEIGHT:
                return True, f"Rule A Interlock: Pump ON commanded while outlet valve is 0% open and level is {h:.2f}m.", alerts

        return False, "", alerts

    def process_command(self, payload: Dict[str, Any]) -> List[Alert]:
        alerts = []
        cmd_name = payload.get("command") or payload.get("action")
        val = payload.get("value")
        sp = payload.get("setpoint")
        h = self.current_state["h"]
        pump = self.current_state["pump"]
        valve = self.current_state["valve"]
        operating_mode = self.current_state.get("mode", "RUNNING")
        is_maintenance = (operating_mode == "MAINTENANCE")

        # Track command frequency for oscillation detection
        osc_anomaly = self.behavior.track_command_frequency()
        if osc_anomaly and not is_maintenance:
            score = self.alert_mgr.calculate_anomaly_score(s_command=0.8, s_temporal=0.7)
            alert = self.alert_mgr.emit_alert(
                key="command_oscillation",
                severity="HIGH",
                layer="4. Temporal & Behavioral",
                what=osc_anomaly["msg"],
                consequence="Rapid actuator cycling causing mechanical wear or process instability.",
                advice="Investigate control source for automated loop hunting or malicious tampering.",
                confidence=0.85,
                anomaly_score=score,
                equipment="PUMP-101 / VALVE-101",
                uncertainty_statement="Confidence 85%: Frequent command changes detected. Verify if operator is tuning loops.",
            )
            if alert:
                alerts.append(alert)

        # Static rules evaluation (Rule A, Rule B)
        if not is_maintenance:
            rule_alerts = self.command.evaluate_static_rules(cmd_name, val, h, valve, pump)
            for r in rule_alerts:
                score = self.alert_mgr.calculate_anomaly_score(s_command=0.9, s_trajectory=0.9)
                equip = "PUMP-101" if cmd_name == "pump" else "VALVE-101"
                alert = self.alert_mgr.emit_alert(
                    key=r["rule"],
                    severity=r["severity"],
                    layer="2. Static Rule Analysis",
                    what=r["what"],
                    consequence=r["consequence"],
                    advice=r["advice"],
                    confidence=r["confidence"],
                    anomaly_score=score,
                    equipment=f"{equip} (TANK-01)",
                    uncertainty_statement=f"High Confidence ({r['confidence']*100:.0f}%). Physical context breach confirmed.",
                    context={"level": h, "pump": pump, "valve": valve}
                )
                if alert:
                    alerts.append(alert)

        # Trajectory forward simulation prediction
        new_pump = val if cmd_name == "pump" and val is not None else pump
        new_valve = val if cmd_name == "valve" and val is not None else valve

        if not is_maintenance:
            h_pred, eta_of, eta_dry = self.physics.forward_simulate(h, new_pump, new_valve)
            if eta_of is not None:
                sev = "CRITICAL" if eta_of <= 30.0 else "HIGH"
                score = self.alert_mgr.calculate_anomaly_score(s_trajectory=0.95, s_command=0.7)
                alert = self.alert_mgr.emit_alert(
                    key="model_overfill_trajectory",
                    severity=sev,
                    layer="3. Physics Model Trajectory",
                    what=f"Pump command ({new_pump*100:.0f}%) while valve is {new_valve*100:.0f}% open will drive level to safe ceiling {cfg.MAX_SAFE_HEIGHT:.2f}m in {eta_of:.1f}s (predicted {h_pred:.2f}m).",
                    consequence="Imminent tank overflow and vessel rupture.",
                    advice="Reduce inlet pump flow or open outlet valve V-101.",
                    confidence=0.90,
                    anomaly_score=score,
                    equipment="PUMP-101 / TANK-01",
                    uncertainty_statement="Confidence 90%: ODE shadow model predicts overfill trajectory under current actuation.",
                    context={"level": h, "eta_seconds": eta_of, "predicted_level": h_pred}
                )
                if alert:
                    alerts.append(alert)

        if sp is not None:
            drift_anomaly = self.behavior.process_setpoint(float(sp))
            if drift_anomaly:
                score = self.alert_mgr.calculate_anomaly_score(s_command=0.8)
                alert = self.alert_mgr.emit_alert(
                    key="setpoint_drift",
                    severity="HIGH",
                    layer="4. Temporal & Behavioral",
                    what=drift_anomaly["msg"],
                    consequence="Stealthy relocation of process safety boundaries.",
                    advice="Audit setpoint change history and verify operator authorization.",
                    confidence=0.85,
                    anomaly_score=score
                )
                if alert:
                    alerts.append(alert)

        return alerts


def main():
    detector = AnomalyDetector()
    client = ICSCMQTTClient(client_id="security-detector")

    def on_telemetry(topic, payload):
        alerts = detector.process_telemetry(payload)
        for a in alerts:
            print(a.render())
            client.publish_json(topics.TOPIC_ALERTS, a.to_dict())
            client.publish_json(topics.LEGACY_TOPIC_ALERTS, a.to_dict())

    def on_command(topic, payload):
        alerts = detector.process_command(payload)
        for a in alerts:
            print(a.render())
            client.publish_json(topics.TOPIC_ALERTS, a.to_dict())
            client.publish_json(topics.LEGACY_TOPIC_ALERTS, a.to_dict())

    client.subscribe(topics.TOPIC_TELEMETRY, on_telemetry)
    client.subscribe(topics.LEGACY_TOPIC_TELEMETRY, on_telemetry)
    client.subscribe(topics.TOPIC_COMMANDS, on_command)
    client.subscribe(topics.LEGACY_TOPIC_COMMANDS, on_command)

    client.connect()
    print("[*] ICSC Process-Aware Anomaly Detector running (Advisory Monitor). Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[*] Security Detector stopped.")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
