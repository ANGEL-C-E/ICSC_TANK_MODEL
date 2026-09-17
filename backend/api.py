"""
Control Backend API interface unifying Auth, Gateway, and Vulnerable paths.
"""

from typing import Any, Dict, Tuple
from backend.auth import AuthService
from backend.vulnerability import VulnerableBackendEndpoint
from control.command_gateway import CommandGateway


class BackendAPI:
    def __init__(self, command_gateway: CommandGateway):
        self.gateway = command_gateway
        self.vulnerable_endpoint = VulnerableBackendEndpoint(command_gateway)

    @staticmethod
    def login(username: str, password: str) -> Tuple[bool, str, Dict[str, Any]]:
        return AuthService.login(username, password)

    def submit_command(self, token: str, raw_command: str) -> Tuple[bool, str, Dict[str, Any]]:
        return self.gateway.process_raw_command(token, raw_command, source="backend_api")

    def submit_vulnerable_command(self, token: str, raw_command: str) -> Tuple[bool, str, Dict[str, Any]]:
        return self.vulnerable_endpoint.exploit_submit_command(token, raw_command)
