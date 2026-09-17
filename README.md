# Industrial Control System Simulation (ICSC) Tank Model Testbed

A production-grade, 6-plane Cyber-Physical System (CPS) ICS Testbed modeling a single-tank water process with Torricelli mass-balance ODE physics, dynamic actuator lag ($\tau=0.5\text{s}$), MQTT transport, SQLite persistence, role-based authorization (RBAC), an interactive operator terminal, an out-of-band SOC security dashboard, and an advisory-only process-aware security detector.

Built specifically for CPS/ICS cybersecurity research, threat analysis, and security engineering: the anomaly detector continuously monitors the control bus, evaluating every command and telemetry sample against the physical rules of the plant and physical consequences. In accordance with industrial safety standards, **the security monitor acts strictly as an advisory system** (`SECURITY_MODE = "ADVISORY"`): it alerts human engineers, but never automatically trips or blocks plant operation.

---

## System Architecture (6-Plane CPS Testbed)

```
                       +-----------------------------------+
                       |         MQTT Broker (ics/*)       |
                       +-----------------------------------+
                        ^                 ^               ^
         telemetry/live |                 |               | advisories
             (JSON)     |                 |               |   (JSON)
                        v                 v               v
               +---------------+  +---------------+  +---------------+
               | Physical Plant|  | Control Plane |  | Security SOC  |
               | Tank / Pump / |  | Operator CLI  |  | Detector &    |
               | Outflow Valve |  | & RBAC Gateway|  | Dashboard     |
               +---------------+  +---------------+  +---------------+
                        ^                 ^               ^
                        +-----------------+---------------+
                                          |
                                 +------------------+
                                 |  SQLite Storage  |
                                 | (icsc_testbed.db)|
                                 +------------------+
```

### Module Plane Breakdown

| Plane / Directory | Module Purpose & Key Components |
| :--- | :--- |
| **`core/`** | Core configurations ([config.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/core/config.py)), SQLite persistence manager ([database.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/core/database.py)), domain models ([models.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/core/models.py)), and schemas ([schemas.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/core/schemas.py)). |
| **`plant/`** | Torricelli & mass-balance ODE solver ([tank.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/plant/tank.py)), first-order actuator dynamic lag ($\tau=0.5\text{s}$) ([pump.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/plant/pump.py), [valve.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/plant/valve.py)), sensor noise & fault injection ([sensors.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/plant/sensors.py)), state machine controller ([controller.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/plant/controller.py)). |
| **`control/`** | Finite command grammar registry ([command_registry.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/control/command_registry.py)), RBAC matrix ([authorization.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/control/authorization.py)), session manager ([sessions.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/control/sessions.py)), command gateway ([command_gateway.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/control/command_gateway.py)). |
| **`security/`** | Advisory-only detection engine ([detector.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/security/detector.py)), shadow ODE residual detector ([physics_detector.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/security/physics_detector.py)), temporal/sequence anomaly detector ([temporal_detector.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/security/temporal_detector.py)), setpoint drift detector ([behavioral_detector.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/security/behavioral_detector.py)), pre-actuation rule checker ([command_detector.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/security/command_detector.py)), and contextual alert formatter ([alert_manager.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/security/alert_manager.py)). |
| **`backend/`** | FastAPI REST API backend ([api.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/backend/api.py)), authentication router ([auth.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/backend/auth.py)), and deliberate vulnerability endpoint ([vulnerability.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/backend/vulnerability.py)). |
| **`mqtt/`** | Embedded MQTT broker adapter ([broker.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/mqtt/broker.py)), topic definitions ([topics.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/mqtt/topics.py)), and paho client wrapper ([client.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/mqtt/client.py)). |
| **`scenarios/`** | 12 operational & cyber-attack simulation scripts ([scenarios/](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/scenarios)). |
| **`cli/`** | Command Line Interfaces for Operator Console ([cli/operator.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/cli/operator.py)), Attacker Console ([cli/attacker.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/cli/attacker.py)), and SOC Dashboard ([cli/monitor.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/cli/monitor.py)). |
| **`tests/`** | Automated pytest verification suite ([tests/](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/tests)). |

---

## Physical Dynamics & Governing Equations

The process simulates a fluid storage tank obeying mass-balance and Torricelli's law of efflux, integrated over continuous time step $dt$:

1. **Inflow Dynamics** (Pump flow rate $u_{\text{pump}} \in [0, 1]$):
   $$Q_{\text{in}}(t) = u_{\text{pump}}(t) \cdot Q_{\text{pump,max}}$$

2. **Outflow Dynamics** (Torricelli's law for orifice discharge with valve opening $u_{\text{valve}} \in [0, 1]$):
   $$Q_{\text{out}}(t) = u_{\text{valve}}(t) \cdot Q_{\text{valve,max}} \cdot \sqrt{\frac{h(t)}{h_{\text{max}}}}$$

3. **Mass Balance Differential Equation**:
   $$\frac{dh}{dt} = \frac{Q_{\text{in}}(t) - Q_{\text{out}}(t)}{A}$$

4. **Actuator Dynamic Lag ($\tau = 0.5\text{s}$)**:
   Actuators do not step instantaneously; pump speed and valve position follow first-order response differential equations:
   $$\frac{du}{dt} = \frac{u_{\text{target}} - u}{\tau}$$

5. **Hydrostatic Pressure**:
   $$P = \rho \cdot g \cdot h(t)$$

---

## Operational & Safety Parameters

All operational thresholds are defined centrally in [core/config.py](file:///home/Ace/gitfiles/icsc/branch/ICSC_TANK_MODEL/core/config.py):

| Parameter | Value | Unit | Description |
| :--- | :--- | :--- | :--- |
| `TANK_AREA` | `1.0` | m² | Tank cross-sectional area |
| `MAX_LEVEL` | `2.0` | m | Physical tank overflow limit |
| `MAX_SAFE_HEIGHT` | `1.8` | m | Maximum safe height before overfill advisory |
| `MIN_SAFE_HEIGHT` | `0.2` | m | Minimum safe height before dry-run advisory |
| `MAX_SAFE_PRESSURE` | `17.65` | kPa | Maximum hydrostatic pressure threshold |
| `SECURITY_MODE` | `"ADVISORY"` | — | Non-blocking out-of-band advisory mode |

---

## Database Schema & Seeding

The system uses an SQLite database (`icsc_testbed.db`) for audit trails, session handling, user identity, and telemetry logging. **All database binary files (`*.db`) are ignored by Git (`.gitignore`) to maintain repository hygiene.**

### Seeding the Database
To initialize database tables and create standard user accounts, run:

```bash
python seed_db.py
```

### Pre-Seeded Default Accounts

| Username | Password | Role | Permissions / Privileges |
| :--- | :--- | :--- | :--- |
| `operator_01` | `operator123` | `OPERATOR` | Execute `pump`, `valve`, `setpoint`, `reset` |
| `engineer_01` | `engineer123` | `ENGINEER` | Execute all operator commands + `maintenance on/off` |
| `supervisor_01` | `super123` | `SUPERVISOR` | Full administrative override & maintenance control |
| `security_01` | `sec123` | `SECURITY_ANALYST` | Read-only access to security dashboard & advisories |
| `attacker_01` | `guest` | `GUEST` | Unprivileged role used to simulate unauthorized access |

---

## Quick Start & Running the Testbed

### 1. Installation

```bash
git clone <repository-url>
cd ICSC_TANK_MODEL
pip install -r requirements.txt
```

### 2. Seed Database
```bash
python seed_db.py
```

### 3. Run Automated Tests
Verify all 13 core engine unit and integration tests:

```bash
pytest -v
```

### 4. Interactive Live Demonstration (3 Terminals)

Open 3 separate terminal windows:

* **Terminal 1 — SOC Security Monitor & Advisory Dashboard**:
  ```bash
  python -m cli.monitor
  ```

* **Terminal 2 — Operator Control Console**:
  ```bash
  python -m cli.operator
  ```

* **Terminal 3 — Attacker Console**:
  ```bash
  python -m cli.attacker
  ```

---

## Executing Attack & Operational Scenarios

You can run individual scenario scripts from `scenarios/` to test specific CPS vulnerabilities:

### Cyber Attack Vectors
* **Wrong-Moment Attack (Dead-heading / Overpressure Hazard)**:
  ```bash
  python -m scenarios.wrong_moment_attack
  ```
  *Sends `PUMP ON` while `VALVE` is closed, causing pressure escalation.*

* **Overfill Attack**:
  ```bash
  python -m scenarios.overfill_attack
  ```

* **Low-and-Slow Setpoint Drift Attack**:
  ```bash
  python -m scenarios.slow_setpoint_drift
  ```

* **Telemetry Replay Attack**:
  ```bash
  python -m scenarios.telemetry_replay_attack
  ```

* **Dry-Run Pump Attack**:
  ```bash
  python -m scenarios.dry_run_attack
  ```

* **Actuator Oscillation Attack**:
  ```bash
  python -m scenarios.oscillation_attack
  ```

### Plant Maintenance Mode
To run testing without triggering security alarms:

```bash
python -m scenarios.legitimate_maintenance
```
*Toggles plant into `MAINTENANCE` state, verifying alarm suppression while logging activity with `[MAINTENANCE ACTIVE]` flags.*

---

## Advisory Security Philosophy

In accordance with industrial control safety guidelines:
1. **Advisory-Only Enforcement**: The security detector evaluates commands and sensor feeds, generating contextual advisories for SOC personnel.
2. **Human-in-the-Loop**: The detector **never automatically trips or blocks** command execution on the control bus (`SECURITY_MODE = "ADVISORY"`).
3. **Equipment-Specific Guidance**: Advisories provide targeted tags (`PUMP-101`, `VALVE-101`, `TANK-01`), physical consequences, actionable operator advice, and uncertainty ratings when confidence is $<0.90$.

---

## Repository Hygiene & Git Push Guidelines

When preparing to commit and push to GitHub:
1. SQLite database files (`icsc_testbed.db`, `*.db`) and Python bytecode (`__pycache__`) are automatically ignored via `.gitignore`.
2. Always execute `pytest -v` to ensure all tests pass prior to committing.
