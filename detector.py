"""
Process-aware anomaly detector for the ICSC tank plant.

Listens on the plant MQTT bus, evaluates every telemetry sample and command
against the physical rules of the tank, and raises human-readable advisories.

It is an ADVISORY system only: it never publishes commands or actuates the
plant. Alerts are printed to stdout (engineer dashboard) and mirrored as JSON
on the alerts topic for dashboards.

Detection pipeline (per message):

    Layer 1  Syntax & sanity filter     malformed, out-of-bounds, sensor-inconsistent
    Layer 2  Static rule-based          Rule A overfill context, Rule B dry-run
                                        context, Rule C pressure limit
    Layer 3  Physics / model-based      ODE "shadow simulation" of the tank:
                                        overfill/dry prediction + telemetry
                                        spoofing/replay divergence check
    Layer 4  Temporal & behavioral      stale/replayed telemetry, frozen feed
                                        while pump is on, setpoint drift

Message schemas
---------------
Telemetry (plant/telemetry), published by the simulation:
    {"ts": 1690000000.0, "seq": 42, "level": 0.85, "inflow": 0.4,
     "outflow": 0.1, "pump_pct": 0.8, "valve_pct": 0.25, "pressure": 8340.0}

Commands (plant/commands), published by operators:
    {"action": "pump",     "value": 1.0,  "label": "PUMP_ON"}   # value: 0..1
    {"action": "valve",    "value": 0.5}                        # value: 0..1
    {"action": "setpoint", "setpoint": 0.7}                     # meters
"""

import json
import math
import time

import config as cfg
from mqtt_common import connect, make_client

# Consecutive identical-level samples (while the pump is running) tolerated
# before the feed is considered frozen/replayed.
_FROZEN_EPS = 1e-9


# --------------------------------------------------------------------------
# Alert object
# --------------------------------------------------------------------------
class Alert:
    """A single engineer-readable advisory."""

    def __init__(self, severity, layer, what_happened, consequence, advice,
                 confidence, context=None):
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.unix_ts = time.time()
        self.device_id = cfg.DEVICE_ID
        self.severity = severity
        self.layer = layer
        self.what_happened = what_happened
        self.consequence = consequence
        self.advice = advice
        self.confidence = confidence
        self.context = context if context is not None else {}

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "unix_ts": self.unix_ts,
            "device_id": self.device_id,
            "severity": self.severity,
            "layer": self.layer,
            "what_happened": self.what_happened,
            "physical_context": self.context,
            "predicted_consequence": self.consequence,
            "confidence": self.confidence,
            "action_advice": self.advice,
        }

    def render(self):
        bar = "=" * 64
        return (
            f"\n{bar}\n"
            f"[SECURITY ADVISORY - {self.severity}] "
            f"(confidence {self.confidence * 100:.0f}%)\n"
            f"Device:      {self.device_id}\n"
            f"Layer:       {self.layer}\n"
            f"What:        {self.what_happened}\n"
            f"Context:     {self._context_text()}\n"
            f"Consequence: {self.consequence}\n"
            f"Advice:      {self.advice}\n"
            f"{bar}\n"
        )

    def _context_text(self):
        if not self.context:
            return "n/a"
        parts = []
        if "level" in self.context:
            parts.append(f"level {self.context['level']:.2f} m")
        if "pressure_kpa" in self.context:
            parts.append(f"pressure {self.context['pressure_kpa']:.2f} kPa")
        if "valve_pct" in self.context:
            parts.append(f"valve {self.context['valve_pct'] * 100:.0f}%")
        if "pump_pct" in self.context:
            parts.append(f"pump {self.context['pump_pct'] * 100:.0f}%")
        return " | ".join(parts)


def _physical_context(state):
    return {
        "level": state.get("h", 0.0),
        "pressure_kpa": state.get("pressure", 0.0) / 1000.0,
        "valve_pct": state.get("valve", 0.0),
        "pump_pct": state.get("pump", 0.0),
    }


def _clamp01(x):
    return max(0.0, min(1.0, x))


# --------------------------------------------------------------------------
# Detector core (pure logic, no MQTT - easy to unit test)
# --------------------------------------------------------------------------
class AnomalyDetector:
    def __init__(self):
        # Last known plant state (canonical keys: h, valve, pump, q_in, q_out, pressure)
        self.state = {
            "h": 0.5,
            "valve": 0.6,
            "pump": 0.0,
            "q_in": 0.0,
            "q_out": 0.0,
            "pressure": cfg.RHO * cfg.G * 0.5,
        }
        self.last_telemetry_time = time.time()

        # Shadow (parallel) simulation state for the ODE bridge
        self.shadow_h = self.state["h"]
        self.shadow_time = time.time()

        # Temporal / behavioral tracking
        self.last_seq = None
        self.last_h = None
        self.frozen_count = 0
        self.setpoint_history = []  # list of (timestamp, setpoint)

        # Alert de-duplication: rule key -> last emit time
        self._cooldowns = {}

    # ------------------------------------------------------------------
    # Alert emission with per-rule cooldown
    # ------------------------------------------------------------------
    def _emit(self, key, severity, layer, what, consequence, advice,
              confidence, context=None):
        now = time.time()
        last = self._cooldowns.get(key)
        if last is not None and now - last < cfg.ALERT_COOLDOWN:
            return None
        self._cooldowns[key] = now
        return Alert(severity, layer, what, consequence, advice, confidence,
                     context if context is not None else _physical_context(self.state))

    # ------------------------------------------------------------------
    # Layer 3 helper: forward Euler simulation of the tank ODE
    # ------------------------------------------------------------------
    def _forward_simulate(self, pump, valve, h, horizon=None, dt=None):
        """Shadow-simulate the tank; return (h_final, eta_overfill, eta_dry).

        eta_overfill / eta_dry: seconds until the level crosses
        MAX_SAFE_HEIGHT / MIN_SAFE_HEIGHT, or None if it does not within
        the horizon.
        """
        horizon = cfg.PREDICTION_HORIZON if horizon is None else horizon
        dt = cfg.PREDICTION_DT if dt is None else dt

        h_sim = h
        eta_overfill = None
        eta_dry = None
        steps = max(1, int(horizon / dt))
        for i in range(1, steps + 1):
            q_in = pump * cfg.MAX_PUMP_FLOW
            q_out = valve * cfg.MAX_OUTFLOW * math.sqrt(max(h_sim, 0.0) / cfg.MAX_LEVEL)
            h_sim += (q_in - q_out) / cfg.TANK_AREA * dt
            h_sim = min(max(h_sim, 0.0), cfg.MAX_LEVEL)
            if eta_overfill is None and h_sim >= cfg.MAX_SAFE_HEIGHT:
                eta_overfill = i * dt
            if eta_dry is None and h_sim <= cfg.MIN_SAFE_HEIGHT:
                eta_dry = i * dt
            if h_sim <= 0.0 or h_sim >= cfg.MAX_LEVEL:
                break
        return h_sim, eta_overfill, eta_dry

    # ------------------------------------------------------------------
    # Layer 1: validation
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_telemetry(payload):
        if not isinstance(payload, dict):
            return False, "payload is not a JSON object"
        level = payload.get("level")
        if not isinstance(level, (int, float)) or isinstance(level, bool):
            return False, "missing or non-numeric 'level'"
        if not 0.0 <= level <= cfg.MAX_LEVEL:
            return False, f"'level' {level} outside physical bounds [0, {cfg.MAX_LEVEL}]"
        for key in ("pump_pct", "valve_pct"):
            if key in payload:
                v = payload[key]
                if not isinstance(v, (int, float)) or isinstance(v, bool) \
                        or not 0.0 <= v <= 1.0:
                    return False, f"'{key}' must be a number in [0, 1]"
        return True, ""

    @staticmethod
    def _validate_command(payload):
        if not isinstance(payload, dict):
            return False, "payload is not a JSON object", None
        action = payload.get("action")
        if action not in ("pump", "valve", "setpoint"):
            return False, f"unknown action {action!r}", None
        if action == "setpoint":
            sp = payload.get("setpoint")
            if not isinstance(sp, (int, float)) or isinstance(sp, bool):
                return False, "setpoint command requires numeric 'setpoint'", None
            if not 0.0 <= sp <= cfg.MAX_LEVEL:
                return False, f"setpoint {sp} outside physical bounds", None
        else:
            value = payload.get("value")
            if not isinstance(value, (int, float)) or isinstance(value, bool) \
                    or not 0.0 <= value <= 1.0:
                return False, f"'{action}' command requires numeric 'value' in [0, 1]", None
        return True, "", payload

    # ------------------------------------------------------------------
    # Telemetry path
    # ------------------------------------------------------------------
    def process_telemetry(self, payload):
        """Feed a telemetry sample through the pipeline. Returns [Alert, ...]."""
        now = time.time()

        # --- Layer 1: syntax & sanity ---
        ok, err = self._validate_telemetry(payload)
        if not ok:
            alert = self._emit(
                "syntax-telemetry", "CRITICAL", "1. Syntax & Sanity",
                f"Malformed telemetry blocked: {err}.",
                "Detector is operating on stale state; spoofing or corruption possible.",
                "Inspect the telemetry publisher and network path.",
                0.95)
            return [alert] if alert else []

        h = float(payload["level"])
        valve = float(payload.get("valve_pct", self.state["valve"]))
        pump = float(payload.get("pump_pct", self.state["pump"]))
        pressure = payload.get("pressure", cfg.RHO * cfg.G * h)
        seq = payload.get("seq")
        ts = payload.get("ts")

        alerts = []

        # --- Layer 4: sequence / timestamp replay checks ---
        if seq is not None and self.last_seq is not None:
            if seq <= self.last_seq:
                alert = self._emit(
                    "seq-replay", "HIGH", "4. Temporal & Behavioral",
                    f"Telemetry sequence number went backwards or repeated "
                    f"({self.last_seq} -> {seq}).",
                    "Messages may be replayed or the feed is duplicated.",
                    "Verify the publisher is live and unique; check for MITM.",
                    0.85)
                if alert:
                    alerts.append(alert)
            elif seq - self.last_seq > cfg.SEQUENCE_GAP_MAX:
                alert = self._emit(
                    "seq-gap", "WARNING", "4. Temporal & Behavioral",
                    f"Gap of {seq - self.last_seq} in telemetry sequence numbers.",
                    "Samples may have been dropped or suppressed.",
                    "Check broker/publisher health for message loss.",
                    0.70)
                if alert:
                    alerts.append(alert)
        if ts is not None:
            if ts > now + cfg.REPLAY_TIME_TOLERANCE:
                alert = self._emit(
                    "ts-future", "WARNING", "4. Temporal & Behavioral",
                    "Telemetry timestamp is in the future.",
                    "Clock skew or fabricated sample.",
                    "Synchronize clocks (NTP) and verify the publisher.",
                    0.70)
                if alert:
                    alerts.append(alert)
            elif now - ts > cfg.REPLAY_TIME_TOLERANCE:
                alert = self._emit(
                    "ts-stale", "WARNING", "4. Temporal & Behavioral",
                    f"Telemetry sample is {now - ts:.1f}s older than receipt time.",
                    "Sample may be replayed from history.",
                    "Check for caching or recording/replay in the pipeline.",
                    0.70)
                if alert:
                    alerts.append(alert)

        # --- Layer 3: ODE shadow-model divergence (spoof / replay check) ---
        dt = min(max(now - self.shadow_time, 0.0), cfg.PREDICTION_HORIZON)
        predicted_h = self.shadow_h + dt * (self.state["q_in"] - self.state["q_out"]) / cfg.TANK_AREA
        predicted_h = min(max(predicted_h, 0.0), cfg.MAX_LEVEL)
        divergence = abs(predicted_h - h)
        if dt >= cfg.PREDICTION_DT and divergence > cfg.REPLAY_TOLERANCE:
            alert = self._emit(
                "spoof", "HIGH", "3. Physics / Model-Based",
                f"Reported level {h:.3f} m deviates {divergence:.3f} m from the "
                f"ODE shadow-model prediction ({predicted_h:.3f} m).",
                "Telemetry may be spoofed, replayed, or the sensor is failing.",
                "Cross-check level sensor against a second measurement.",
                0.85 if divergence > 5 * cfg.REPLAY_TOLERANCE else 0.70)
            if alert:
                alerts.append(alert)

        # --- Layer 4: frozen feed while pump is running ---
        if self.last_h is not None and pump > 0.05 and self.state["pump"] > 0.05:
            if abs(h - self.last_h) < _FROZEN_EPS:
                self.frozen_count += 1
                if self.frozen_count >= cfg.FROZEN_SAMPLES:
                    alert = self._emit(
                        "frozen", "WARNING", "4. Temporal & Behavioral",
                        f"Level frozen at {h:.3f} m for {self.frozen_count} samples "
                        f"while the pump is running.",
                        "Telemetry is stale or replayed; the plant state is unknown.",
                        "Verify the telemetry publisher and sensor wiring.",
                        0.80)
                    if alert:
                        alerts.append(alert)
            else:
                self.frozen_count = 0
        else:
            self.frozen_count = 0

        # --- Layer 2: Rule C - pressure limit & sensor sanity ---
        if pressure > cfg.MAX_SAFE_PRESSURE:
            alert = self._emit(
                "rule-c", "CRITICAL", "2. Static Rule (C: Pressure Limit)",
                f"Hydrostatic pressure {pressure / 1000.0:.2f} kPa exceeds the "
                f"safe limit {cfg.MAX_SAFE_PRESSURE / 1000.0:.2f} kPa "
                f"(P = rho*g*h at h = {cfg.MAX_SAFE_HEIGHT} m).",
                "Immediate over-pressure risk to the vessel.",
                "Reduce the level: close the pump and/or open the outlet valve.",
                0.95)
            if alert:
                alerts.append(alert)
        expected_p = cfg.RHO * cfg.G * h
        if expected_p > 0 and abs(pressure - expected_p) > \
                cfg.PRESSURE_SENSOR_TOLERANCE * expected_p:
            alert = self._emit(
                "pressure-inconsistent", "WARNING", "1. Syntax & Sanity",
                f"Reported pressure {pressure / 1000.0:.2f} kPa is inconsistent "
                f"with level {h:.2f} m (expected {expected_p / 1000.0:.2f} kPa).",
                "Pressure sensor or level reading is unreliable.",
                "Calibrate/verify pressure and level sensors.",
                0.70)
            if alert:
                alerts.append(alert)

        # --- Update internal state & resync shadow model ---
        self.state.update({
            "h": h,
            "valve": valve,
            "pump": pump,
            "q_in": float(payload.get("inflow", pump * cfg.MAX_PUMP_FLOW)),
            "q_out": float(payload.get("outflow",
                                       valve * cfg.MAX_OUTFLOW
                                       * math.sqrt(max(h, 0.0) / cfg.MAX_LEVEL))),
            "pressure": float(pressure),
        })
        self.last_telemetry_time = now
        self.last_seq = seq if seq is not None else self.last_seq
        self.last_h = h
        self.shadow_h = h
        self.shadow_time = now

        return [a for a in alerts if a is not None]

    # ------------------------------------------------------------------
    # Command path
    # ------------------------------------------------------------------
    def process_command(self, payload):
        """Evaluate a command against the current plant state. Returns [Alert, ...]."""
        now = time.time()

        # --- Layer 1: syntax & sanity ---
        ok, err, cmd = self._validate_command(payload)
        if not ok:
            alert = self._emit(
                "syntax-command", "CRITICAL", "1. Syntax & Sanity",
                f"Malformed command blocked: {err}.",
                "Unvalidated input reached the actuation path.",
                "Reject the command; audit the source of the message.",
                0.95)
            return [alert] if alert else []

        action = cmd["action"]
        value = cmd.get("value")
        label = cmd.get("label", "")
        h = self.state["h"]
        valve = self.state["valve"]
        pump = self.state["pump"]
        alerts = []
        fired = set()

        # --- Layer 4: temporal health at decision time ---
        if now - self.last_telemetry_time > cfg.TELEMETRY_STALE_AFTER:
            alert = self._emit(
                "stale", "WARNING", "4. Temporal & Behavioral",
                f"No telemetry for {now - self.last_telemetry_time:.0f}s "
                f"(threshold {cfg.TELEMETRY_STALE_AFTER:.0f}s).",
                "Command is being evaluated without real-time physical feedback; "
                "possible replay or disconnection.",
                "Restore the telemetry stream before trusting command decisions.",
                0.75)
            if alert:
                alerts.append(alert)

        if action == "pump":
            new_pump = _clamp01(value)
            turning_on = value > 1e-6

            # --- Layer 2: Rule A (overfill context) ---
            if turning_on and valve <= 1e-6 and h > cfg.RULE_A_HEIGHT:
                fired.add("rule-a")
                alert = self._emit(
                    "rule-a", "CRITICAL", "2. Static Rule (A: Overfill Context)",
                    f"Pump ON ({label or f'{value * 100:.0f}%'}) commanded while "
                    f"the outlet valve is 0% open and the tank is at {h:.2f} m.",
                    "Imminent tank overfill and pressure spike.",
                    "Open the outlet valve before energizing the pump.",
                    0.95)
                if alert:
                    alerts.append(alert)

            # --- Layer 2: Rule B (drainage context) ---
            if not turning_on and valve >= 0.99 and h < cfg.MIN_SAFE_HEIGHT:
                fired.add("rule-b")
                alert = self._emit(
                    "rule-b", "WARNING", "2. Static Rule (B: Drainage Context)",
                    f"Pump OFF commanded with the valve 100% open and the tank "
                    f"nearly empty ({h:.2f} m).",
                    "Tank will drain dry; downstream pump may lose prime and run dry.",
                    "Close the outlet valve or raise the level before draining further.",
                    0.85)
                if alert:
                    alerts.append(alert)

            # --- Layer 3: ODE prediction with the commanded actuation ---
            h_pred, eta_of, eta_dry = self._forward_simulate(new_pump, valve, h)
            if eta_of is not None and "rule-a" not in fired:
                severity = "CRITICAL" if eta_of <= 30.0 else "HIGH"
                alert = self._emit(
                    "model-overfill", severity, "3. Physics / Model-Based",
                    f"Command would drive the level from {h:.2f} m to "
                    f"{cfg.MAX_SAFE_HEIGHT:.2f} m within the "
                    f"{cfg.PREDICTION_HORIZON:.0f}s horizon "
                    f"(predicted {h_pred:.2f} m).",
                    "Tank breaches the safe operating height, causing overflow.",
                    "Reduce pump flow or open the outlet valve first.",
                    0.90)
                if alert:
                    alerts.append(alert)
            if eta_dry is not None and "rule-b" not in fired:
                alert = self._emit(
                    "model-dry", "WARNING", "3. Physics / Model-Based",
                    f"Command would drain the tank below {cfg.MIN_SAFE_HEIGHT:.2f} m "
                    f"within the {cfg.PREDICTION_HORIZON:.0f}s horizon.",
                    "Tank runs dry; pump cavitation and equipment damage possible.",
                    "Close the outlet valve or reduce outflow.",
                    0.80)
                if alert:
                    alerts.append(alert)

        elif action == "valve":
            new_valve = _clamp01(value)

            # --- Layer 3: ODE prediction with the commanded valve position ---
            h_pred, eta_of, eta_dry = self._forward_simulate(pump, new_valve, h)
            if eta_of is not None:
                severity = "CRITICAL" if eta_of <= 30.0 else "HIGH"
                alert = self._emit(
                    "model-overfill", severity, "3. Physics / Model-Based",
                    f"With the valve at {new_valve * 100:.0f}% and the pump "
                    f"running, the level reaches {cfg.MAX_SAFE_HEIGHT:.2f} m "
                    f"within the {cfg.PREDICTION_HORIZON:.0f}s horizon.",
                    "Tank breaches the safe operating height, causing overflow.",
                    "Reduce pump flow or open the valve further.",
                    0.90)
                if alert:
                    alerts.append(alert)
            if eta_dry is not None:
                alert = self._emit(
                    "model-dry", "WARNING", "3. Physics / Model-Based",
                    f"Valve at {new_valve * 100:.0f}% drains the tank below "
                    f"{cfg.MIN_SAFE_HEIGHT:.2f} m (from {h:.2f} m) within the "
                    f"{cfg.PREDICTION_HORIZON:.0f}s horizon.",
                    "Tank runs dry; pump cavitation and equipment damage possible.",
                    "Close the outlet valve or reduce outflow.",
                    0.80)
                if alert:
                    alerts.append(alert)

        elif action == "setpoint":
            sp = float(cmd["setpoint"])
            self.setpoint_history.append((now, sp))

            # --- Layer 4: setpoint drift over a sliding window ---
            cutoff = now - cfg.SETPOINT_DRIFT_WINDOW
            self.setpoint_history = [(t, s) for (t, s) in self.setpoint_history
                                     if t >= cutoff]
            if len(self.setpoint_history) >= 3:
                values = [s for (_, s) in self.setpoint_history]
                drift = max(values) - min(values)
                if drift > cfg.SETPOINT_DRIFT_LIMIT:
                    alert = self._emit(
                        "setpoint-drift", "HIGH", "4. Temporal & Behavioral",
                        f"Cumulative setpoint drift of {drift:.2f} m within "
                        f"{cfg.SETPOINT_DRIFT_WINDOW:.0f}s "
                        f"({len(values)} changes).",
                        "Stealthy relocation of operating limits toward an unsafe regime.",
                        "Audit the setpoint change trail and verify operator identity.",
                        0.85)
                    if alert:
                        alerts.append(alert)

        if not alerts:
            return []
        return [a for a in alerts if a is not None]


# --------------------------------------------------------------------------
# MQTT wiring
# --------------------------------------------------------------------------
detector = AnomalyDetector()


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[*] Detector connected to broker (code: {rc})")
    client.subscribe(cfg.TOPIC_TELEMETRY)
    client.subscribe(cfg.TOPIC_COMMANDS)
    print(f"[*] Subscribed: {cfg.TOPIC_TELEMETRY}, {cfg.TOPIC_COMMANDS}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except (ValueError, UnicodeDecodeError) as e:
        alert = detector._emit(
            "syntax-json", "CRITICAL", "1. Syntax & Sanity",
            f"Unparseable message on '{msg.topic}': {e}.",
            "Malformed traffic on the control network.",
            "Identify the sender; enforce schema validation at the broker.",
            0.95)
        if alert:
            _report(client, alert)
        return

    if msg.topic == cfg.TOPIC_TELEMETRY:
        alerts = detector.process_telemetry(payload)
    elif msg.topic == cfg.TOPIC_COMMANDS:
        alerts = detector.process_command(payload)
    else:
        return

    for alert in alerts:
        _report(client, alert)


def _report(client, alert):
    print(alert.render())
    client.publish(cfg.TOPIC_ALERTS, json.dumps(alert.to_dict()))


def main():
    client = make_client(on_connect, on_message)
    connect(client)
    print("[*] ICSC anomaly detector running (advisory-only, no actuation).")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[*] Detector stopped.")


if __name__ == "__main__":
    main()
