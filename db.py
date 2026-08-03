"""
Database access layer for the Trekking Management Application.
Uses plain sqlite3 (no ORM) as per project requirement: SQLite only, no other DB.
All tables are created programmatically - never edit trekking.db by hand.
"""
import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trekking.db")

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


def get_db_connection():
    """Return a new sqlite3 connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables (if they don't already exist) and seed the admin account."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'staff', 'user')),
            name TEXT NOT NULL,
            contact TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS treks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            difficulty TEXT NOT NULL CHECK(difficulty IN ('Easy', 'Moderate', 'Hard')),
            duration INTEGER NOT NULL,
            total_slots INTEGER NOT NULL,
            available_slots INTEGER NOT NULL,
            assigned_staff_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Pending'
                CHECK(status IN ('Pending', 'Approved', 'Open', 'Closed', 'Completed')),
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (assigned_staff_id) REFERENCES accounts(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            trek_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Booked'
                CHECK(status IN ('Booked', 'Cancelled', 'Completed')),
            FOREIGN KEY (user_id) REFERENCES accounts(id),
            FOREIGN KEY (trek_id) REFERENCES treks(id)
        )
    """)

    conn.commit()

    # Seed the pre-existing admin account (no admin self-registration allowed)
    existing = cur.execute(
        "SELECT id FROM accounts WHERE role = 'admin' LIMIT 1"
    ).fetchone()
    if not existing:
        cur.execute(
            """INSERT INTO accounts
               (username, email, password_hash, role, name, contact, status, created_at)
               VALUES (?, ?, ?, 'admin', ?, ?, 'active', ?)""",
            (
                DEFAULT_ADMIN_USERNAME,
                "admin@trekapp.local",
                generate_password_hash(DEFAULT_ADMIN_PASSWORD),
                "System Admin",
                "N/A",
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        print(f"[init_db] Seeded default admin -> "
              f"username: '{DEFAULT_ADMIN_USERNAME}' password: '{DEFAULT_ADMIN_PASSWORD}'")

    conn.close()
