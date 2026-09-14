"""
Shared configuration for the ICSC tank system.

Every component (simulation, detector, operator) imports from here so the
physics constants, safety limits and MQTT topic names never drift apart.
"""

# --- MQTT Topics ---
# Telemetry:  plant/telemetry          (JSON state of the plant)
# Commands:   plant/commands           (JSON action requests from operators)
# Alerts:     plant/alerts             (detector advisories, JSON)
TOPIC_TELEMETRY = "plant/telemetry"
TOPIC_COMMANDS = "plant/commands"
TOPIC_ALERTS = "plant/alerts"

# --- Tank Physical Parameters ---
TANK_AREA = 1.0        # Cross-sectional area A (m^2)
MAX_LEVEL = 10.0       # Maximum liquid height h_max (m)
MAX_PUMP_FLOW = 0.5    # Maximum inflow at 100% pump (m^3/s)
MAX_OUTFLOW = 0.4      # Maximum outflow at 100% valve & full tank (m^3/s)

RHO = 1000             # Water density (kg/m^3)
G = 9.81               # Gravity acceleration (m/s^2)

# --- Safety Limits (detector thresholds) ---
MAX_SAFE_HEIGHT = 0.90   # h above this -> overfill risk (m)
MIN_SAFE_HEIGHT = 0.10   # h below this -> tank dry / pump damage risk (m)
MAX_SAFE_PRESSURE = RHO * G * MAX_SAFE_HEIGHT  # P = rho * g * h (Pa)
RULE_A_HEIGHT = 0.80     # h above this + pump on + valve closed -> critical context

# --- Detection Engine Settings ---
# Note: the simulated tank supports levels up to MAX_LEVEL (10 m), but the
# safety envelope is intentionally narrower (0.10 - 0.90 m) per the
# challenge brief. MAX_SAFE_HEIGHT is an OPERATING limit, not a hard wall.
PREDICTION_HORIZON = 60.0     # Forward-simulation horizon (s)
PREDICTION_DT = 0.1           # Shadow-model Euler step (s)
TELEMETRY_STALE_AFTER = 10.0  # s without telemetry -> temporal alert
REPLAY_TOLERANCE = 0.10       # m; telemetry deviation tolerated vs shadow model
# (must exceed level change per telemetry interval ~ q_in/A * dt so normal
#  jitter or a dropped message doesn't trigger it)
REPLAY_TIME_TOLERANCE = 5.0   # s; age of timestamp tolerated before spoof alert
SEQUENCE_GAP_MAX = 5          # Allowed gap in sequence numbers before replay alert
SETPOINT_DRIFT_WINDOW = 300.0 # Sliding window for drift analysis (s)
SETPOINT_DRIFT_LIMIT = 0.3    # Cumulative setpoint movement that triggers alert (m)
FROZEN_SAMPLES = 5            # Telemetry samples with identical h while pump is on -> frozen feed
PRESSURE_SENSOR_TOLERANCE = 0.15  # Relative deviation of reported P from rho*g*h tolerated

ALERT_COOLDOWN = 5.0   # s; minimum delay between repeat alerts of the same layer

# --- MQTT Broker ---
BROKER = "localhost"
PORT = 1883
KEEPALIVE = 60

# --- Identity ---
DEVICE_ID = "TANK-01"  # physical device the telemetry describes

