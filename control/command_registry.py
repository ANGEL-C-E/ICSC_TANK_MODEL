"""
Finite Command Registry defining the valid control vocabulary of the testbed.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple, Type
import core.config as cfg


class BaseCommand(ABC):
    name: str = ""

    @classmethod
    @abstractmethod
    def validate_args(cls, tokens: list) -> Tuple[bool, str, Dict[str, Any]]:
        pass


class PumpCommand(BaseCommand):
    name = "pump"

    @classmethod
    def validate_args(cls, tokens: list) -> Tuple[bool, str, Dict[str, Any]]:
        if len(tokens) < 2:
            return False, "Usage: pump <0-100>", {}
        try:
            val = float(tokens[1])
            if not (0.0 <= val <= 100.0):
                return False, "Pump percentage must be in range [0, 100]", {}
            pct = val / 100.0
            label = "PUMP_ON" if pct > 0 else "PUMP_OFF"
            return True, "", {"action": "pump", "command": "pump", "value": pct, "label": label}
        except ValueError:
            return False, f"Invalid numeric value: '{tokens[1]}'", {}


class ValveCommand(BaseCommand):
    name = "valve"

    @classmethod
    def validate_args(cls, tokens: list) -> Tuple[bool, str, Dict[str, Any]]:
        if len(tokens) < 2:
            return False, "Usage: valve <0-100>", {}
        try:
            val = float(tokens[1])
            if not (0.0 <= val <= 100.0):
                return False, "Valve percentage must be in range [0, 100]", {}
            return True, "", {"action": "valve", "command": "valve", "value": val / 100.0}
        except ValueError:
            return False, f"Invalid numeric value: '{tokens[1]}'", {}


class SetpointCommand(BaseCommand):
    name = "setpoint"

    @classmethod
    def validate_args(cls, tokens: list) -> Tuple[bool, str, Dict[str, Any]]:
        if len(tokens) < 2:
            return False, f"Usage: setpoint <0-{cfg.MAX_LEVEL}>", {}
        try:
            sp = float(tokens[1])
            if not (0.0 <= sp <= cfg.MAX_LEVEL):
                return False, f"Setpoint must be in range [0, {cfg.MAX_LEVEL}] meters", {}
            return True, "", {"action": "setpoint", "command": "setpoint", "setpoint": sp}
        except ValueError:
            return False, f"Invalid numeric setpoint: '{tokens[1]}'", {}


class EstopCommand(BaseCommand):
    name = "estop"

    @classmethod
    def validate_args(cls, tokens: list) -> Tuple[bool, str, Dict[str, Any]]:
        return True, "", {"action": "estop", "command": "estop", "value": 0.0, "label": "EMERGENCY_STOP"}


class ResetCommand(BaseCommand):
    name = "reset"

    @classmethod
    def validate_args(cls, tokens: list) -> Tuple[bool, str, Dict[str, Any]]:
        return True, "", {"action": "reset", "command": "reset"}


class MaintenanceCommand(BaseCommand):
    name = "maintenance"

    @classmethod
    def validate_args(cls, tokens: list) -> Tuple[bool, str, Dict[str, Any]]:
        mode = tokens[1].lower() if len(tokens) >= 2 else "on"
        if mode not in ("on", "off", "start", "stop"):
            return False, "Usage: maintenance <on/off>", {}
        return True, "", {"action": "maintenance", "command": "maintenance", "mode": mode}


class CommandRegistry:
    _commands: Dict[str, Type[BaseCommand]] = {
        "pump": PumpCommand,
        "valve": ValveCommand,
        "setpoint": SetpointCommand,
        "estop": EstopCommand,
        "reset": ResetCommand,
        "maintenance": MaintenanceCommand,
    }

    @classmethod
    def is_registered(cls, name: str) -> bool:
        return name.lower() in cls._commands

    @classmethod
    def parse_command(cls, raw_line: str) -> Tuple[bool, str, Dict[str, Any]]:
        tokens = raw_line.strip().split()
        if not tokens:
            return False, "Empty command line", {}
        cmd_name = tokens[0].lower()
        if not cls.is_registered(cmd_name):
            return False, f"Command '{cmd_name}' is not in the finite control vocabulary.", {}
        cmd_cls = cls._commands[cmd_name]
        return cmd_cls.validate_args(tokens)
