"""
Session manager backed by SQLite database.
"""

from typing import Any, Dict, Optional
from core.database import db
from core.models import SessionInfo


class SessionManager:
    @staticmethod
    def create_session(user_id: str, username: str, role: str, ttl_seconds: float = 3600.0) -> SessionInfo:
        token = db.create_session(user_id, username, role, ttl_seconds)
        return SessionInfo(
            token=token,
            user_id=user_id,
            username=username,
            role=role,
        )

    @staticmethod
    def validate_session(token: str) -> Optional[Dict[str, Any]]:
        return db.validate_session(token)

    @staticmethod
    def invalidate_session(token: str):
        db.invalidate_session(token)
