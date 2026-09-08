# Industrial Control System Simulation (ICSC)

A lightweight physics-based simulator and telemetry system for modeling single-tank liquid level dynamics in Cyber-Physical Systems (CPS) and Industrial Control Systems (ICS).

---

## 📌 Overview

The **Industrial Control System Simulation (ICSC)** models the physical dynamics of a liquid tank controlled via actuator inputs (pump flow rate and outflow valve percentage). It tracks physics-based system state evolution over discrete time steps and generates real-time telemetry suitable for SCADA integration, control system testing (e.g., PID or Reinforcement Learning controllers), or cybersecurity anomaly detection research.

---

## 🧮 Mathematical Model & Physics

The tank system is modeled using continuous differential equations discretized over time step $dt$:

### 1. Inflow ($Q_{in}$)
Driven by the pump actuator percentage ($u_{pump} \in [0, 1]$):
$$Q_{in} = u_{pump} \cdot \text{MAX\_PUMP\_FLOW}$$

### 2. Outflow ($Q_{out}$)
Driven by Torricelli's Law based on fluid hydrostatic height ($h$) and valve opening percentage ($u_{valve} \in [0, 1]$):
$$Q_{out} = u_{valve} \cdot \text{MAX\_OUTFLOW} \cdot \sqrt{\frac{h}{h_{max}}}$$

### 3. Level Derivative ($\frac{dh}{dt}$)
Mass balance equation governed by cross-sectional tank area ($A$):
$$\frac{dh}{dt} = \frac{Q_{in} - Q_{out}}{A}$$

### 4. Euler Integration & Boundary Constraints
$$h(t + dt) = \text{clip}\left(h(t) + \frac{dh}{dt} \cdot dt, \, 0, \, h_{max}\right)$$

---

## 📐 System Parameters & Constraints

Defined in [server.py](file:///home/Ace/gitfiles/icsc/server.py):

| Parameter | Value | Unit | Description |
| :--- | :--- | :--- | :--- |
| `TANK_AREA` | `1.0` | $\text{m}^2$ | Tank cross-sectional area |
| `MAX_LEVEL` | `10.0` | $\text{m}$ | Maximum liquid height $h_{max}$ |
| `MAX_PUMP_FLOW` | `0.5` | $\text{m}^3/\text{s}$ | Maximum inflow capacity at 100% pump |
| `MAX_OUTFLOW` | `0.4` | $\text{m}^3/\text{s}$ | Maximum outflow capacity at 100% valve & full tank |

---

## 📂 Codebase Structure

```
icsc/
├── server.py       # Core TankModel physics engine & constraints
├── simulation.py   # Simulation execution script & telemetry logger
└── .gitignore      # Git exclusions for Python artifacts
```

### File Descriptions
* **[server.py](file:///home/Ace/gitfiles/icsc/server.py)**: Contains the `TankModel` class managing state variables (`level`, `inflow`, `outflow`, `pump_pct`, `valve_pct`), actuation limits, derivative computation, and numerical state updates.
* **[simulation.py](file:///home/Ace/gitfiles/icsc/simulation.py)**: Instantiates `TankModel`, configures initial actuators, steps through time updates ($\Delta t = 0.01\text{s}$), and emits state telemetry.

---

## 🚀 Getting Started

### Prerequisites
* Python 3.7+
* NumPy

### Installation
Clone the repository and install dependencies:

```bash
git clone https://github.com/your-username/icsc.git
cd icsc
pip install numpy
```

---

## 💻 Usage

### Running the Simulation
To execute the default simulation run and output telemetry logs to the console:

```bash
python simulation.py
```

### Python API Example
You can embed `TankModel` into your own control loops or network servers:

```python
from server import TankModel

# Initialize tank at height of 4.0 meters
tank = TankModel(level=4.0)

# Set actuator inputs (percentages between 0.0 and 1.0)
tank.set_pump(pump_pct=0.8)   # 80% pump speed
tank.set_valve(valve_pct=0.2)  # 20% valve opening

# Run simulation step (dt in seconds)
tank.update(dt=0.01)

# Retrieve telemetry dictionary
state = tank.get_state()
print(f"Current Level: {state['level']:.3f} m | Inflow: {state['inflow']:.3f} | Outflow: {state['outflow']:.3f}")
```

---

## 🛠️ Pushing to GitHub

If initializing a new GitHub repository from this local folder, execute the following commands:

```bash
# 1. Initialize Git repository
git init

# 2. Add files
git add .

# 3. Commit changes
git commit -m "Initial commit: ICSC physical tank simulation model & telemetry engine"

# 4. Link remote repository and push
git branch -M main
git remote add origin https://github.com/<your-username>/icsc.git
git push -u origin main
```
