"""
RBAC Authorization layer for checking role capabilities against control actions.
"""

from typing import List
import core.config as cfg


class AuthorizationManager:
    @staticmethod
    def get_role_capabilities(role: str) -> List[str]:
        return cfg.ROLES.get(role.upper(), [])

    @classmethod
    def is_action_allowed(cls, role: str, action: str) -> bool:
        capabilities = cls.get_role_capabilities(role)
        # Map control actions to capability requirements
        action_capability_map = {
            "pump": "pump_control",
            "valve": "valve_control",
            "setpoint": "setpoint_control",
            "estop": "estop",
            "reset": "reset",
            "maintenance": "configure",
            "status": "view_telemetry",
            "telemetry": "view_telemetry",
            "alarms": "view_alerts",
        }
        required_cap = action_capability_map.get(action.lower())
        if not required_cap:
            return False
        return required_cap in capabilities
