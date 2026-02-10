"""
User database operations.

This module handles all user-related database operations including CRUD
(Create, Read, Update, Delete) operations and password management.

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

import os
import hashlib
import sqlite3
import datetime
from typing import Optional, Dict

from utils.SanitizeOrValidate import (
    valid_input,
    valid_username,
    is_valid_length,
    valid_integer,
)

import utils.constants as c
from utils.exceptions import DBException, ProcessingError


def get_username_and_pass(username: str) -> Optional[Dict]:
    """
    Get user credentials and user_id from database with validation.

    Args:
        username: Username to look up

    Returns:
        Dict with user_id, password_hash, and salt if found, None otherwise
    """
    if not (c.DB_CONNECTION and c.DB_CURSOR):
        c.SERVER_STATE.signal_error("DB not initialized")
        return None

    try:
        # Validate username
        if not valid_input(username):
            raise DBException("Username could be an injection")

        if not valid_username(username):
            raise DBException("Username format invalid")

        with c.DB_LOCK:
            c.DB_CURSOR.execute(
                "SELECT user_id, password_hash, salt FROM users WHERE username = ?",
                (username,),
            )
            row = c.DB_CURSOR.fetchone()

        if not row:
            return None

        return {"user_id": row[0], "password_hash": row[1], "salt": row[2]}
    except DBException as e:
        print(f"Potential sql-attack : {username} - {e}")
        return None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None


def get_user_stats_by_id(user_id: int) -> Dict:
    """
    Get user statistics from database by user_id with validation.

    Args:
        user_id: User's ID

    Returns:
        Dict with user stats or empty dict if not found
    """
    if not (c.DB_CONNECTION and c.DB_CURSOR):
        c.SERVER_STATE.signal_error("DB not initialized")
        return {}

    try:
        # Validate user_id
        if not valid_integer(user_id, min_val=1):
            raise DBException("Invalid user_id")

        with c.DB_LOCK:
            c.DB_CURSOR.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user_data = c.DB_CURSOR.fetchone()

        if not user_data:
            return {}

        return {
            "elo": user_data[4],
            "wins": user_data[5],
            "draws": user_data[6],
            "losses": user_data[7],
            "join_date": user_data[8],
            "last_game": user_data[9],
        }
    except DBException as e:
        print(f"Validation error in get_user_stats_by_id: {e}")
        return {}
    except sqlite3.Error as e:
        print(f"Error: {e}")
        return {}


def create_new_user(username: str, password: str) -> Optional[int]:
    """
    Insert a new user into the database with validation.

    Args:
        username: New username (validated for format and length)
        password: Plain text password (will be hashed)

    Returns:
        The new user's user_id if successful, None otherwise
    """

    if not (c.DB_CONNECTION and c.DB_CURSOR):
        c.SERVER_STATE.signal_error("DB not initialized")
        return None

    try:
        if not valid_username(username):
            raise DBException("Username format invalid")

        if not is_valid_length(username, 3, 20):
            raise DBException("Username length invalid")

        if not valid_input(username):
            raise DBException("Username could be an injection")

        if not valid_input(password):
            raise DBException("Password could contain injection")

        if not is_valid_length(password, 12, 128):
            raise DBException("Password length invalid")

        password_hash, salt = generate_password_hash(password)

        with c.DB_LOCK:
            c.DB_CURSOR.execute(
                "SELECT user_id FROM users WHERE username = ?",
                (username,),
            )
            if c.DB_CURSOR.fetchone():
                raise ProcessingError("Username already exists", 409)

            c.DB_CURSOR.execute(
                """
                INSERT INTO users (username, password_hash, salt, elo, wins, draws, losses, join_date, last_game)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    password_hash,
                    salt,
                    500,
                    0,
                    0,
                    0,
                    datetime.datetime.now().isoformat(),
                    None,
                ),
            )
            c.DB_CONNECTION.commit()
            user_id = c.DB_CURSOR.lastrowid
        print(f"User {username} added successfully!")
        return user_id
    except DBException as e:
        print(f"Validation error in create_new_user : {username} - {e}")
        return None
    except sqlite3.IntegrityError:
        return None


def generate_password_hash(password: str, salt: Optional[bytes] = None) -> tuple:
    """
    Generate a SHA512 hash of the given password and an optional salt.

    Args:
        password: Plain text password
        salt: Optional salt bytes (generated if not provided)

    Returns:
        tuple: (hashed_password_hex, salt_hex)
    """
    if not salt:
        salt = os.urandom(16)
    hash_obj = hashlib.sha512(salt + password.encode())
    hashed_password = hash_obj.hexdigest()
    return hashed_password, salt.hex()


def compare_password(password: str, hashed_password: str, salt: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        password: Plain text password to verify
        hashed_password: Stored password hash (hex string)
        salt: Salt used for hashing (hex string)

    Returns:
        True if password matches, False otherwise
    """
    return generate_password_hash(password, bytes.fromhex(salt))[0] == hashed_password


def update_username(user_id: int, new_username: str) -> bool:
    """
    Update a user's username in the database with validation.

    Args:
        user_id: User's ID (immutable identifier)
        new_username: New username to set

    Returns:
        True if successful, False if username already exists or error occurs
    """

    if not (c.DB_CONNECTION and c.DB_CURSOR):
        c.SERVER_STATE.signal_error("DB not initialized")
        return False

    try:
        # Validate user_id
        if not valid_integer(user_id, min_val=1):
            raise DBException("Invalid user_id")

        if not valid_input(new_username):
            raise DBException("New username could be an injection")

        if not valid_username(new_username):
            raise DBException("New username format invalid")

        if not is_valid_length(new_username, 3, 20):
            raise DBException("New username length invalid")

        with c.DB_LOCK:
            # Check if new username already exists
            c.DB_CURSOR.execute(
                "SELECT user_id FROM users WHERE username = ?",
                (new_username,),
            )
            if c.DB_CURSOR.fetchone():
                return False

            # Update username
            c.DB_CURSOR.execute(
                "UPDATE users SET username = ? WHERE user_id = ?",
                (new_username, user_id),
            )
            c.DB_CONNECTION.commit()

        print(f"Username updated for user_id {user_id} -> {new_username}")
        return True
    except DBException as e:
        print(f"Validation error in update_username : {new_username} - {e}")
        return False
    except sqlite3.Error as e:
        print(f"Error updating username: {e}")
        return False


def update_password(user_id: int, new_password: str) -> bool:
    """
    Update a user's password in the database with validation.

    Args:
        user_id: User's ID
        new_password: New password (plain text, will be hashed)

    Returns:
        True if successful, False otherwise
    """
    if not (c.DB_CONNECTION and c.DB_CURSOR):
        c.SERVER_STATE.signal_error("DB not initialized")
        return False

    try:
        # Validate user_id
        if not valid_integer(user_id, min_val=1):
            raise DBException("Invalid user_id")

        # Validate password
        if not valid_input(new_password):
            raise DBException("Password could contain injection")

        if not is_valid_length(new_password, 12, 128):
            raise DBException("Password length invalid")

        password_hash, salt = generate_password_hash(new_password)

        with c.DB_LOCK:
            c.DB_CURSOR.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE user_id = ?",
                (password_hash, salt, user_id),
            )
            c.DB_CONNECTION.commit()

        print(f"Password updated for user_id: {user_id}")
        return True
    except DBException as e:
        print(f"Validation error in update_password: {e}")
        return False
    except sqlite3.Error as e:
        print(f"Error updating password: {e}")
        return False


def delete_user_account(user_id: int) -> bool:
    """
    Delete a user account from the database with validation.

    Args:
        user_id: User ID of account to delete

    Returns:
        True if successful, False otherwise
    """
    if not (c.DB_CONNECTION and c.DB_CURSOR):
        c.SERVER_STATE.signal_error("DB not initialized")
        return False

    try:
        # Validate user_id
        if not valid_integer(user_id, min_val=1):
            raise DBException("Invalid user_id")

        with c.DB_LOCK:
            c.DB_CURSOR.execute(
                "DELETE FROM users WHERE user_id = ?",
                (user_id,),
            )
            c.DB_CONNECTION.commit()

        print(f"Account deleted: {user_id}")
        return True
    except DBException as e:
        print(f"Validation error in delete_user_account: {e}")
        return False
    except sqlite3.Error as e:
        print(f"Error deleting account: {e}")
        return False
