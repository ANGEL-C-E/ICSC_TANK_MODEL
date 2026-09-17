"""
Integration tests for operational and attack scenarios.
"""

from scenarios import (
    command_injection,
    legitimate_maintenance,
    normal_running,
    slow_setpoint_drift,
    startup_shutdown,
    telemetry_replay_attack,
    wrong_moment_attack,
)


def test_scenario_execution():
    assert normal_running.run_scenario()["status"] == "SUCCESS"
    assert startup_shutdown.run_scenario()["status"] == "SUCCESS"
    assert legitimate_maintenance.run_scenario()["status"] == "SUCCESS"
    assert command_injection.run_scenario()["status"] == "ATTACK_EXECUTED"
    assert wrong_moment_attack.run_scenario()["status"] == "ATTACK_EXECUTED"
    assert slow_setpoint_drift.run_scenario()["status"] == "ATTACK_EXECUTED"
    assert telemetry_replay_attack.run_scenario()["status"] == "ATTACK_EXECUTED"
