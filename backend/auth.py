"""
Authentication service issuing session tokens upon successful authentication.
"""

from typing import Any, Dict, Tuple
from backend.users import UserStore
from control.sessions import SessionManager
from core.database import db
from core.events import EventType


class AuthService:
    @staticmethod
    def login(username: str, password: str) -> Tuple[bool, str, Dict[str, Any]]:
        user = UserStore.authenticate(username, password)
        if not user:
            db.log_audit_event(
                event_type=EventType.AUTH_FAILURE,
                action="login",
                status="failed",
                details={"username": username, "reason": "Invalid credentials"}
            )
            return False, "Authentication failed: invalid username or password.", {}

        session = SessionManager.create_session(
            user_id=user["user_id"],
            username=user["username"],
            role=user["role"]
        )

        db.log_audit_event(
            event_type=EventType.LOGIN,
            action="login",
            status="success",
            user_id=user["user_id"],
            session_id=session.token,
            details={"role": user["role"]}
        )

        return True, "Login successful.", {
            "token": session.token,
            "username": session.username,
            "role": session.role,
            "expires_at": session.expires_at,
        }
