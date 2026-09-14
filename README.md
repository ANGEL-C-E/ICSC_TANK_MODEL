# Industrial Control System Simulation (ICSC)

A physics-based single-tank liquid level simulator with MQTT telemetry, an
interactive operator console, and a process-aware security anomaly detector
that monitors the plant bus in real time.

Built for CPS/ICS security research: the detector evaluates every command and
telemetry sample against the physical rules of the tank and raises
human-readable advisories — it advises, it never actuates.

---

## Architecture

```
                +---------------------+
                |   MQTT Broker       |   localhost:1883 (e.g. mosquitto)
                +---------------------+
                 ^         ^         ^
      telemetry  |         |         |  alerts
     (JSON)      |         |         |  (JSON)
                 |         |         |
        +--------+--+   +--+--------+---+   +-------------+
        | simulation |  |  operator     |   |  detector   |
        | TankModel  |  |  console CLI  |   |  4-layer    |
        | + MQTT     |  +--+------------+   |  monitor    |
        +--------^---+     |  commands     +------^------+
                 |         +-----------------------+
                 |              commands (JSON)
                 |
          physical plant (tank ODE)
```

* **simulation.py** runs the plant physics in real time, publishes telemetry
  on `plant/telemetry`, applies commands from `plant/commands`.
* **operator_console.py** is the engineer console: sends pump/valve/setpoint commands
  and displays live state and advisories.
* **detector.py** silently observes both topics, runs every message through a
  4-layer detection pipeline, prints engineer-readable alerts to stdout and
  mirrors them as JSON on `plant/alerts`.

### MQTT topics

| Topic             | Direction        | Payload                                      |
| :---------------- | :--------------- | :------------------------------------------- |
| `plant/telemetry` | sim → bus        | `{"ts", "seq", "level", "inflow", "outflow", "pump_pct", "valve_pct", "pressure"}` |
| `plant/commands`  | operator → bus   | `{"action": "pump"\|"valve"\|"setpoint", "value"\|"setpoint": number, "label"?: string}` |
| `plant/alerts`    | detector → bus   | full alert object (see below)                |

---

## The Physics

The tank is modeled with mass balance and Torricelli's law, discretized with
Euler integration over time step $dt$:

**Inflow** (driven by pump percentage $u_{pump} \in [0,1]$):

$$Q_{in} = u_{pump} \cdot \text{MAX\_PUMP\_FLOW}$$

**Outflow** (driven by valve percentage $u_{valve} \in [0,1]$ and hydrostatic head):

$$Q_{out} = u_{valve} \cdot \text{MAX\_OUTFLOW} \cdot \sqrt{\frac{h}{h_{max}}}$$

**Level dynamics** (mass balance over cross-sectional area $A$):

$$\frac{dh}{dt} = \frac{Q_{in} - Q_{out}}{A}$$

**Integration & bounds**:

$$h(t+dt) = \text{clip}\left(h(t) + \frac{dh}{dt} \cdot dt,\ 0,\ h_{max}\right)$$

**Hydrostatic pressure** reported in telemetry: $P = \rho \, g \, h$.

### Physical parameters (`config.py`)

| Parameter         | Value            | Unit       | Description                          |
| :---------------- | :--------------- | :--------- | :----------------------------------- |
| `TANK_AREA`       | `1.0`            | m²         | Tank cross-sectional area            |
| `MAX_LEVEL`       | `10.0`           | m          | Hard physical maximum height         |
| `MAX_PUMP_FLOW`   | `0.5`            | m³/s       | Max inflow at 100% pump              |
| `MAX_OUTFLOW`     | `0.4`            | m³/s       | Max outflow at 100% valve, full tank |
| `RHO`             | `1000`           | kg/m³      | Water density                        |
| `G`               | `9.81`           | m/s²       | Gravity                              |

### Safety envelope (`config.py`)

The tank can physically hold 10 m, but the detector guards a narrower
operating band:

| Limit               | Value  | Meaning                                        |
| :------------------ | :----- | :--------------------------------------------- |
| `MAX_SAFE_HEIGHT`   | 0.90 m | Above: overfill risk → alerts                  |
| `MIN_SAFE_HEIGHT`   | 0.10 m | Below: dry-run / cavitation risk → alerts      |
| `MAX_SAFE_PRESSURE` | ρg·0.90 ≈ 8.83 kPa | Over-pressure limit (Rule C)       |

---

## The Anomaly Detector

`detector.py` is a process-aware security monitor. Every MQTT message passes
through:

```
Incoming MQTT message
        |
        v
1. Syntax & sanity filter ......... malformed JSON, out-of-bounds values,
 |                                  pressure inconsistent with level
 v
2. Static rule-based checks ....... Rule A (overfill context),
 |                                  Rule B (drainage context),
 |                                  Rule C (pressure limit)
 v
3. Physics / model-based engine ... ODE "shadow simulation": forward-Euler
 |                                  prediction of h(k+1..k+N) from the same
 |                                  equation the plant uses; flags commands
 |                                  that will overfill/dry the tank, and
 |                                  telemetry that diverges from the model
 v                                  (spoofing / replay)
4. Temporal & behavioral .......... stale telemetry, sequence replays/gaps,
                                    frozen level while pump runs, setpoint
                                    drift over a sliding window
```

### Detection rules

| Rule | Trigger | Severity | Consequence flagged |
| :--- | :------ | :------- | :------------------ |
| **A — Overfill context** | Pump ON while valve 0% and h > 0.80 m | CRITICAL | Imminent overfill and pressure spike |
| **B — Drainage context** | Pump OFF while valve 100% and h < 0.10 m | WARNING | Tank drains dry, pump loses prime |
| **C — Pressure limit** | Reported P > ρg·h_safe | CRITICAL | Over-pressure risk |
| **Model overfill** | Shadow sim predicts h crosses 0.90 m under the commanded actuation | CRITICAL/HIGH (by time-to-breach) | Overflow |
| **Model dry-out** | Shadow sim predicts h falls below 0.10 m | WARNING | Cavitation, equipment damage |
| **Telemetry spoof** | Reported h diverges from shadow-model prediction | HIGH | Spoofing / replay / sensor fault |
| **Stale feed** | No telemetry > 10 s (or old timestamps) | WARNING | Decisions without physical feedback |
| **Replay** | Sequence numbers repeat/backwards or future timestamps | HIGH/WARNING | Replayed traffic |
| **Frozen feed** | Level unchanged for 5 samples while pump runs | WARNING | Stale or replayed telemetry |
| **Setpoint drift** | Setpoint moves > 0.30 m cumulatively within a 300 s window | HIGH | Stealthy relocation of operating limits |

### Alert format

Alerts are printed to stdout and mirrored to `plant/alerts` as JSON:

```
================================================================
[SECURITY ADVISORY - CRITICAL] (confidence 95%)
Device:      TANK-01
Layer:       2. Static Rule (A: Overfill Context)
What:        Pump ON (PUMP_ON) commanded while the outlet valve is 0% open
             and the tank is at 0.85 m.
Context:     level 0.85 m | pressure 8.34 kPa | valve 0% | pump 0%
Consequence: Imminent tank overfill and pressure spike.
Advice:      Open the outlet valve before energizing the pump.
================================================================
```

JSON form: `timestamp`, `unix_ts`, `device_id`, `severity`
(`INFO`/`WARNING`/`HIGH`/`CRITICAL`), `layer`, `what_happened`,
`physical_context`, `predicted_consequence`, `confidence`, `action_advice`.

Per-rule cooldown (5 s) prevents alert storms from repeated violations.

---

## Getting Started

### Prerequisites

* Python 3.8+
* An MQTT broker on localhost:1883 (e.g. [mosquitto](https://mosquitto.org/):
  `mosquitto -v`)

### Installation

```bash
git clone <repo-url> && cd icsc
pip install -r requirements.txt
```

### Running (3 terminals)

```bash
mosquitto -v          # 1. the broker
python simulation.py  # 2. the plant (starts at 0.5 m, mid safety band)
python detector.py    # 3. the security monitor
python operator_console.py  # 4. (optional) drive the plant
```

### Operator console example

```
operator> valve 0
[>] Sent: {"action": "valve", "value": 0.0}
operator> pump 100
[>] Sent: {"action": "pump", "value": 1.0, "label": "PUMP_ON"}

[SECURITY ADVISORY - CRITICAL] (confidence 90%)
...
```

### Python API

```python
from server import TankModel

tank = TankModel(level=0.5)

tank.set_pump(pump_pct=0.8)     # 80% pump speed
tank.set_valve(valve_pct=0.2)   # 20% valve opening

tank.update(dt=0.01)            # one physics step

state = tank.get_state()
print(f"Level: {state['level']:.3f} m | In: {state['inflow']:.3f} | "
      f"Out: {state['outflow']:.3f}")
```

### Configuration

All thresholds (safety heights, drift limits, stale timeouts, prediction
horizon, broker address) live in `config.py` — one source of truth shared by
the simulation, the detector and the operator console.

### Testing the detector

With all three processes running:

1. **Rule A**: `operator> valve 0` then `pump 100` (tank above 0.8 m) → CRITICAL.
2. **Model check**: watch advisories fire before the level actually crosses
   the safe band.
3. **Spoof detection**: publish a fake level from another terminal —
   `mosquitto_pub -t plant/telemetry -m '{"level": 0.1, "pump_pct": 1.0, "valve_pct": 0.1}'`
   → divergence alert.
4. **Replay**: re-publish an old telemetry message → sequence-number alert.
5. **Setpoint drift**: send several small setpoint changes summing to > 0.3 m
   within 5 minutes → drift alert.

---

## Project Structure

```
icsc/
├── config.py        # Shared physics constants, safety limits, MQTT topics
├── server.py        # TankModel physics engine
├── mqtt_client.py   # MQTT bridge: commands in, telemetry out
├── simulation.py    # Plant entry point (real-time loop)
├── detector.py      # 4-layer process-aware anomaly detector
├── operator_console.py  # Interactive operator console
├── mqtt_common.py   # paho-mqtt 1.x/2.x compatibility helper
└── requirements.txt
```
