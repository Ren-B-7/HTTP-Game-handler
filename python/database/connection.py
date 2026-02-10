"""
Database initialization and connection management.

This module provides database initialization functionality with proper
validation and error handling.

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

import sqlite3

import utils.constants as c

from utils.config import resolve_path
from utils.SanitizeOrValidate import valid_input, is_valid_length


def init_database(db_name: str) -> None:
    """
    Initialize database with validation.

    Creates the main database connection and sets up the users table
    with proper schema including ELO ratings, win/loss records, and
    timestamps.

    Args:
        db_name: Database filename (validated for security)

    Returns:
        None

    Raises:
        Sets SERVER_STATE error on failure
    """
    # Validate database name
    if not valid_input(db_name) or not is_valid_length(db_name, 1, 255):
        c.SERVER_STATE.signal_error("Invalid database name")
        return

    db_path = resolve_path(c.SCRIPT_DIR, db_name)

    try:
        # Create connection with thread-safe settings
        connection = sqlite3.connect(
            db_path,
            check_same_thread=False,
            isolation_level=None,  # Auto-commit mode
        )
        cursor = connection.cursor()

        # Update global references
        c.DB_CONNECTION = connection
        c.DB_CURSOR = cursor

        # Create users table with proper schema
        with c.DB_LOCK:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    elo INTEGER NOT NULL DEFAULT 500,
                    wins INTEGER NOT NULL DEFAULT 0,
                    draws INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    join_date TEXT NOT NULL,
                    last_game TEXT
                )
            """)

        print(f"✓ Database initialized: {db_path}")

    except Exception as e:
        c.SERVER_STATE.signal_error(f"Database initialization failed: {e}")
