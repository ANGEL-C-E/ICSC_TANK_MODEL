"""
SQLite database storage manager for ICSC testbed persistence.

Handles:
- User identity, password hashing (SHA-256 with salt), and RBAC roles
- Active session token storage and expiration
- High-frequency plant telemetry logging for post-incident analysis
- Immutable audit logs (LOGIN, COMMAND, ACK, AUTHORIZATION_FAILURE, BACKEND_ACCESS)
- Security alert records and anomaly scores
"""

import hashlib
import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

import core.config as cfg


class DatabaseManager:
    """Thread-safe SQLite database manager for ICSC testbed."""

    def __init__(self, db_path: str = cfg.DB_PATH):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create tables if they do not exist and seed default accounts."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Users table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """)

            # 2. Sessions table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """)

            # 3. Telemetry Logs table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                seq INTEGER NOT NULL,
                level REAL NOT NULL,
                pressure REAL NOT NULL,
                pump_pct REAL NOT NULL,
                valve_pct REAL NOT NULL,
                inflow REAL NOT NULL,
                outflow REAL NOT NULL,
                operating_mode TEXT NOT NULL
            )
            """)

            # 4. Audit Events table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                user_id TEXT,
                session_id TEXT,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                details_json TEXT
            )
            """)

            # 5. Security Alerts table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                severity TEXT NOT NULL,
                layer TEXT NOT NULL,
                what_happened TEXT NOT NULL,
                anomaly_score REAL NOT NULL,
                predicted_consequence TEXT NOT NULL,
                action_advice TEXT NOT NULL,
                confidence REAL NOT NULL,
                context_json TEXT
            )
            """)

            conn.commit()

        # Seed default users if empty
        self.seed_default_users()

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

    def seed_default_users(self):
        """Seed default personnel identities into SQLite."""
        default_users = [
            ("user-01", "operator_01", "operator123", "OPERATOR"),
            ("user-02", "engineer_01", "engineer123", "ENGINEER"),
            ("user-03", "supervisor_01", "super123", "SUPERVISOR"),
            ("user-04", "security_01", "sec123", "SECURITY_ANALYST"),
            ("user-05", "attacker_01", "guest", "GUEST"),
        ]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for uid, username, password, role in default_users:
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                if not cursor.fetchone():
                    salt = os.urandom(8).hex()
                    pwd_hash = self._hash_password(password, salt)
                    cursor.execute(
                        "INSERT INTO users (id, username, password_hash, salt, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (uid, username, pwd_hash, salt, role, time.time())
                    )
            conn.commit()

    # --- User & Auth operations ---
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if not row:
                return None
            pwd_hash = self._hash_password(password, row["salt"])
            if pwd_hash == row["password_hash"]:
                return {
                    "user_id": row["id"],
                    "username": row["username"],
                    "role": row["role"]
                }
            return None

    def create_session(self, user_id: str, username: str, role: str, ttl_seconds: float = 3600.0) -> str:
        token = "sess-" + os.urandom(12).hex()
        now = time.time()
        expires_at = now + ttl_seconds
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (token, user_id, username, role, created_at, expires_at, is_active) VALUES (?, ?, ?, ?, ?, ?, 1)",
                (token, user_id, username, role, now, expires_at)
            )
            conn.commit()
        return token

    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE token = ? AND is_active = 1", (token,))
            row = cursor.fetchone()
            if not row:
                return None
            if time.time() > row["expires_at"]:
                cursor.execute("UPDATE sessions SET is_active = 0 WHERE token = ?", (token,))
                conn.commit()
                return None
            return {
                "token": row["token"],
                "user_id": row["user_id"],
                "username": row["username"],
                "role": row["role"],
                "expires_at": row["expires_at"]
            }

    def invalidate_session(self, token: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE sessions SET is_active = 0 WHERE token = ?", (token,))
            conn.commit()

    # --- Logging operations ---
    def log_telemetry(self, telemetry: Dict[str, Any], operating_mode: str = "RUNNING"):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO telemetry_logs 
                   (timestamp, seq, level, pressure, pump_pct, valve_pct, inflow, outflow, operating_mode)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    telemetry.get("ts", time.time()),
                    telemetry.get("seq", 0),
                    telemetry.get("level", 0.0),
                    telemetry.get("pressure", 0.0),
                    telemetry.get("pump_pct", 0.0),
                    telemetry.get("valve_pct", 0.0),
                    telemetry.get("inflow", 0.0),
                    telemetry.get("outflow", 0.0),
                    operating_mode
                )
            )
            conn.commit()

    def log_audit_event(self, event_type: str, action: str, status: str,
                        user_id: Optional[str] = None, session_id: Optional[str] = None,
                        details: Optional[Dict[str, Any]] = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO audit_events
                   (timestamp, event_type, user_id, session_id, action, status, details_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    time.time(),
                    event_type,
                    user_id,
                    session_id,
                    action,
                    status,
                    json.dumps(details) if details else None
                )
            )
            conn.commit()

    def log_alert(self, alert_dict: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO security_alerts
                   (timestamp, severity, layer, what_happened, anomaly_score,
                    predicted_consequence, action_advice, confidence, context_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    alert_dict.get("unix_ts", time.time()),
                    alert_dict.get("severity", "UNKNOWN"),
                    alert_dict.get("layer", ""),
                    alert_dict.get("what_happened", ""),
                    alert_dict.get("anomaly_score", 0.0),
                    alert_dict.get("predicted_consequence", ""),
                    alert_dict.get("action_advice", ""),
                    alert_dict.get("confidence", 0.0),
                    json.dumps(alert_dict.get("physical_context", {}))
                )
            )
            conn.commit()

    # --- Query API ---
    def get_recent_telemetry(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM telemetry_logs ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_audit_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM security_alerts ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_blocked_attacks_count(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM audit_events WHERE event_type = 'ATTACK_BLOCKED'")
            row = cursor.fetchone()
            return row[0] if row else 0


# Global database instance singleton
db = DatabaseManager()
