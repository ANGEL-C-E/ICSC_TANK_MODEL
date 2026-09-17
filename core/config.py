"""
Shared configuration for the ICSC Cyber-Physical System (CPS) testbed.

Contains physical constants, safety boundaries, detection parameters,
MQTT topic hierarchy, database configuration, and default user credentials.
"""

import os
import pathlib

# --- Paths ---
BASE_DIR = pathlib.Path(__file__).parent.parent.resolve()
DB_PATH = os.environ.get("ICSC_DB_PATH", str(BASE_DIR / "icsc_testbed.db"))

# --- MQTT Broker & Port ---
BROKER = os.environ.get("ICSC_BROKER", "localhost")
PORT = int(os.environ.get("ICSC_PORT", "1883"))
KEEPALIVE = 60
DEVICE_ID = "TANK-01"

# --- Structured MQTT Topic Taxonomy ---
TOPIC_AUTH_LOGIN = "ics/auth/login"
TOPIC_AUTH_EVENTS = "ics/auth/events"

TOPIC_COMMANDS = "ics/control/commands"
TOPIC_COMMAND_ACKS = "ics/control/acknowledgements"
TOPIC_CONTROL_EVENTS = "ics/control/events"

TOPIC_TELEMETRY = "ics/plant/telemetry"
TOPIC_PLANT_STATE = "ics/plant/state"
TOPIC_PLANT_EVENTS = "ics/plant/events"

TOPIC_ALERTS = "ics/security/alerts"
TOPIC_SECURITY_EVENTS = "ics/security/events"
TOPIC_SECURITY_INTERLOCKS = "ics/security/interlocks"

TOPIC_AUDIT_EVENTS = "ics/audit/events"

# --- Security Mode ---
# "ADVISORY": Passive out-of-band monitoring and alert logging only (Human-in-the-loop decisions)
# "ACTIVE": Intrusion prevention mode
SECURITY_MODE = os.environ.get("ICSC_SECURITY_MODE", "ADVISORY")

# Legacy topic mappings for backwards compatibility
LEGACY_TOPIC_TELEMETRY = "plant/telemetry"
LEGACY_TOPIC_COMMANDS = "plant/commands"
LEGACY_TOPIC_ALERTS = "plant/alerts"

# --- Tank Physical Parameters ---
TANK_AREA = 1.0        # Cross-sectional area A (m^2)
MAX_LEVEL = 10.0       # Maximum physical height h_max (m)
MAX_PUMP_FLOW = 0.5    # Max inflow at 100% pump (m^3/s)
MAX_OUTFLOW = 0.4      # Max outflow at 100% valve & full tank (m^3/s)

RHO = 1000             # Liquid density (kg/m^3)
G = 9.81               # Acceleration due to gravity (m/s^2)

# --- Actuator Dynamics ---
PUMP_TAU = 0.5         # Pump dynamic time constant (s)
VALVE_TAU = 0.5        # Valve dynamic time constant (s)

# --- Sensor Noise & Precision ---
SENSOR_NOISE_STD = 0.005 # Gaussian noise standard deviation for level sensor (m)

# --- Operating Safety Envelope ---
MAX_SAFE_HEIGHT = 0.90   # Level above this triggers overfill advisory (m)
MIN_SAFE_HEIGHT = 0.10   # Level below this triggers dry-run advisory (m)
MAX_SAFE_PRESSURE = RHO * G * MAX_SAFE_HEIGHT  # Over-pressure limit (Pa) ~ 8.83 kPa
RULE_A_HEIGHT = 0.80     # Threshold for Rule A overfill context (m)

# --- Detection Engine Parameters ---
PREDICTION_HORIZON = 60.0     # Shadow model simulation horizon (s)
PREDICTION_DT = 0.1           # Euler integration step for shadow simulation (s)
TELEMETRY_STALE_AFTER = 10.0  # Telemetry staleness timeout (s)
REPLAY_TOLERANCE = 0.10       # Max deviation (m) allowed between telemetry and shadow model
REPLAY_TIME_TOLERANCE = 5.0   # Max age (s) allowed for telemetry timestamps
SEQUENCE_GAP_MAX = 5          # Max sequence gap allowed before flagging message loss/replay
SETPOINT_DRIFT_WINDOW = 300.0 # Sliding window for setpoint drift (s)
SETPOINT_DRIFT_LIMIT = 0.3    # Max cumulative setpoint movement (m) allowed in window
FROZEN_SAMPLES = 5            # Number of identical level samples while pump runs to trigger frozen feed
PRESSURE_SENSOR_TOLERANCE = 0.15  # Relative deviation of reported P from rho*g*h tolerated

ALERT_COOLDOWN = 5.0   # Minimum delay between repeat alerts of same type (s)

# --- Anomaly Scoring Weights ---
WEIGHT_PHYSICS = 0.30
WEIGHT_TEMPORAL = 0.20
WEIGHT_COMMAND = 0.20
WEIGHT_SENSOR = 0.15
WEIGHT_TRAJECTORY = 0.15

# Anomaly score thresholds
SCORE_NORMAL_MAX = 0.30
SCORE_WATCH_MAX = 0.60
SCORE_WARNING_MAX = 0.80

# --- Default RBAC Personnel ---
ROLES = {
    "OPERATOR": [
        "view_telemetry", "pump_control", "valve_control",
        "setpoint_control", "estop"
    ],
    "ENGINEER": [
        "view_telemetry", "pump_control", "valve_control",
        "setpoint_control", "estop", "reset", "configure"
    ],
    "SUPERVISOR": [
        "view_telemetry", "pump_control", "valve_control",
        "setpoint_control", "estop", "reset", "configure",
        "admin"
    ],
    "SECURITY_ANALYST": [
        "view_telemetry", "view_alerts", "view_audit_logs"
    ]
}
