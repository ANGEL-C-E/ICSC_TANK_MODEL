"""
Unit tests for plant physics, mass balance ODE, and actuator dynamics.
"""

import pytest
import core.config as cfg
from plant.pump import PumpActuator
from plant.tank import TankProcess
from plant.valve import ValveActuator


def test_actuator_dynamic_lag():
    pump = PumpActuator(tau=0.5)
    pump.set_target(1.0)
    assert pump.get_actual_pct() == 0.0

    # Step simulation
    pump.update(dt=0.1)
    assert 0.0 < pump.get_actual_pct() < 1.0

    # Multiple steps converge to target
    for _ in range(20):
        pump.update(dt=0.1)
    assert abs(pump.get_actual_pct() - 1.0) < 0.02


def test_tank_physics_integration():
    tank = TankProcess(initial_level=0.5)
    tank.pump.set_target(0.8)
    tank.valve.set_target(0.0)

    initial_level = tank.level
    for _ in range(10):
        tank.update(dt=0.1)

    # Inflow > Outflow -> Level must increase
    assert tank.level > initial_level
