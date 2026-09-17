"""
User store layer interfacing with SQLite database.
"""

from typing import Any, Dict, Optional
from core.database import db


class UserStore:
    @staticmethod
    def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
        return db.authenticate_user(username, password)
