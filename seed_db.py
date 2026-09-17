"""
Database Seeding Script for ICSC Tank Model Testbed.

Initializes SQLite database tables and seeds default user credentials,
roles, and baseline telemetry if missing.
"""

import sys
from core.database import DatabaseManager, db


def seed_database():
    print("=" * 60)
    print("      ICSC Tank Model - SQLite Database Seeding Utility")
    print("=" * 60)
    
    # Ensuring DB tables exist and seeding default users
    print(f"[*] Initializing database at: {db.db_path}")
    db.seed_default_users()
    
    print("[+] Database tables verified and default accounts seeded successfully.")
    print("\nDefault Account Credentials:")
    print("  - Operator:         username='operator_01'   password='operator123'   role='OPERATOR'")
    print("  - Engineer:         username='engineer_01'   password='engineer123'   role='ENGINEER'")
    print("  - Supervisor:       username='supervisor_01' password='super123'      role='SUPERVISOR'")
    print("  - Security Analyst: username='security_01'   password='sec123'        role='SECURITY_ANALYST'")
    print("  - Guest / Attacker: username='attacker_01'   password='guest'         role='GUEST'")
    print("=" * 60)

if __name__ == "__main__":
    seed_database()
