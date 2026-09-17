"""
Unit tests for Anomaly Detector residual calculation and advisory generation.
"""

from security.detector import AnomalyDetector


def test_rule_a_overfill_context_alert():
    detector = AnomalyDetector()
    detector.current_state["h"] = 0.85
    detector.current_state["valve"] = 0.0

    # Pump 100% while valve 0% and level 0.85m -> Rule A CRITICAL alert
    alerts = detector.process_command({"command": "pump", "value": 1.0})
    assert len(alerts) >= 1
    assert any(a.severity == "CRITICAL" for a in alerts)
    assert any("Rule A" in a.layer or "Trajectory" in a.layer for a in alerts)


def test_residual_divergence_alert():
    detector = AnomalyDetector()
    detector.last_ts = 1000.0

    # Feed telemetry that severely deviates from shadow prediction
    payload = {
        "level": 0.95,  # Jumped from 0.5 to 0.95 unexpectedly
        "pump_pct": 0.0,
        "valve_pct": 0.0,
        "pressure": 9319.5,
        "seq": 1,
        "ts": 1000.1
    }

    alerts = detector.process_telemetry(payload)
    assert len(alerts) >= 1
    assert any("Residual" in a.layer or "Pressure" in a.layer for a in alerts)


def test_pre_actuation_advisory_evaluation():
    detector = AnomalyDetector()
    plant_state = {"h": 0.85, "pressure": 8338.5, "pump": 0.0, "valve": 0.0}

    # Attempt pump 100% when level is 0.85m and valve is 0%
    is_blocked, reason, alerts = detector.evaluate_command_pre_actuation({"command": "pump", "value": 1.0}, plant_state)
    # In ADVISORY mode (core requirement), is_blocked must be False so human operator retains decision power
    assert is_blocked is False
    assert len(alerts) >= 1
    assert any("Rule A" in a.layer or "Trajectory" in a.layer for a in alerts)
