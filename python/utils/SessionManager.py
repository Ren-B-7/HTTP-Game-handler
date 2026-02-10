"""
Efficient Session Manager using SQLite with LRU caching.

This module provides a memory-efficient session management system that uses
SQLite for persistent storage and LRU caching for fast lookups of active
sessions. It uses user_id as the primary identifier instead of username,
making it robust against username changes.

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

import sqlite3
import secrets
import time
from functools import lru_cache
from typing import Optional, Dict
from pathlib import Path


class SessionManager:
    """
    Memory-efficient session manager using SQLite with LRU cache.

    This class manages user sessions with persistent storage and efficient
    in-memory caching. It uses user_id as the primary identifier to ensure
    sessions remain valid even when usernames change.

    Architecture:
        - SQLite database: Persistent storage for all sessions
        - LRU cache: Fast in-memory lookups for active sessions
        - Automatic expiration: Sessions timeout after configured period

    Thread Safety:
        SQLite connection uses check_same_thread=False, making it safe for
        multi-threaded access. Cache operations are inherently thread-safe.

    Attributes:
        db_path (Path): Path to the SQLite database file
        session_timeout (int): Session timeout in seconds
        max_cache_size (int): Maximum sessions to cache in memory
        connection (sqlite3.Connection): Database connection
        get_session: Cached method for retrieving session data
        get_user_sessions: Cached method for retrieving user's sessions

    Example:
        >>> manager = SessionManager(
        ...     db_path=Path("sessions.db"),
        ...     session_timeout=600,
        ...     max_cache_size=1000
        ... )
        >>> session_id = manager.create_session(user_id=1, username="alice", ip="127.0.0.1")
        >>> session = manager.get_session(session_id)
        >>> print(session['username'])
        'alice'
    """

    __slots__ = (
        "db_path",
        "session_timeout",
        "max_cache_size",
        "connection",
        "get_session",
        "get_user_sessions",
        "_cursor",
    )

    def __init__(
        self,
        db_path: Path,
        session_timeout: int = 600,
        max_cache_size: int = 1000,
        max_user_session_cache: int = 250,
    ):
        """
        Initialize session manager with database and caching configuration.

        Args:
            db_path: Path to SQLite database file (created if doesn't exist)
            session_timeout: Session expiration time in seconds (default: 10 minutes)
            max_cache_size: Maximum sessions to cache in memory (default: 1000)
            max_user_session_cache: Maximum user session queries to cache (default: 250)

        """
        self.db_path = db_path
        self.session_timeout = session_timeout
        self.max_cache_size = max_cache_size

        # Allow SQLite connection to be used across threads
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self._cursor = self.connection.cursor()

        # Create cached methods with configured sizes
        # These are instance methods wrapped with lru_cache for optimal performance
        self.get_session = lru_cache(maxsize=max_cache_size)(self._get_session_impl)
        self.get_user_sessions = lru_cache(maxsize=max_user_session_cache)(
            self._get_user_sessions_impl
        )

        self._create_table()

    def _create_table(self):
        """
        Create sessions table and indices if they don't exist.

        Schema:
            session_id (TEXT PRIMARY KEY): Unique session identifier
            user_id (INTEGER NOT NULL): Immutable user database ID
            username (TEXT NOT NULL): Mutable username (for display)
            ip (TEXT NOT NULL): User's IP address
            created_at (INTEGER NOT NULL): Unix timestamp of creation
            last_active (INTEGER NOT NULL): Unix timestamp of last activity

        """
        # Use executescript for atomic schema creation
        self._cursor.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                ip TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                last_active INTEGER NOT NULL
            );
            
            CREATE INDEX IF NOT EXISTS idx_last_active ON sessions(last_active);
            CREATE INDEX IF NOT EXISTS idx_user_id ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_username ON sessions(username);
        """)
        self.connection.commit()

    def create_session(self, user_id: int, username: str, ip: str) -> str:
        """
        Create a new session for a user.

        Args:
            user_id: User's database ID (immutable identifier)
            username: Current username (mutable, for display only)
            ip: User's IP address

        Returns:
            str: Unique session identifier (64-character hex string)

        """
        session_id = secrets.token_hex(32)  # 256 bits of entropy
        now = int(time.time())

        self._cursor.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, user_id, username, ip, now, now),
        )
        self.connection.commit()

        # Clear caches to ensure next lookup gets fresh data
        self._clear_caches()

        return session_id

    def _get_session_impl(self, session_id: str) -> Optional[Dict]:
        """
        Internal implementation of session retrieval (cached via lru_cache).

        Args:
            session_id: Session identifier
        """
        self._cursor.execute(
            "SELECT user_id, username, ip, last_active FROM sessions WHERE session_id = ?",
            (session_id,),
        )

        row = self._cursor.fetchone()
        if not row:
            return None

        user_id, username, ip, last_active = row

        # Check expiration and auto-cleanup expired sessions
        if time.time() - last_active > self.session_timeout:
            self.delete_session(session_id)
            return None

        return {
            "user_id": user_id,
            "username": username,
            "ip": ip,
            "last_active": last_active,
        }

    def update_activity(self, session_id: str) -> bool:
        """
        Update the last_active timestamp for a session.

        This should be called on each request to prevent session expiration
        during active use.

        Args:
            session_id: Session identifier

        Returns:
            bool: True if session was updated, False if session not found
        """
        self._cursor.execute(
            "UPDATE sessions SET last_active = ? WHERE session_id = ?",
            (int(time.time()), session_id),
        )
        self.connection.commit()

        # Only clear caches if we actually updated something
        if self._cursor.rowcount > 0:
            self._clear_caches()
            return True
        return False

    def update_username_in_sessions(self, user_id: int, new_username: str) -> int:
        """
        Update username in all sessions when a user changes their username.

        This method uses user_id to find sessions, ensuring we update the
        correct user even if their old username has already been taken by
        someone else.

        Args:
            user_id: User's database ID (immutable identifier)
            new_username: New username to set in all user's sessions

        Returns:
            int: Number of sessions updated
        """
        self._cursor.execute(
            "UPDATE sessions SET username = ? WHERE user_id = ?",
            (new_username, user_id),
        )
        self.connection.commit()

        count = self._cursor.rowcount
        if count > 0:
            self._clear_caches()
            print(f"Updated username in {count} sessions for user_id {user_id}")

        return count

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session (e.g., on logout).

        Args:
            session_id: Session identifier to delete

        Returns:
            bool: True if session was deleted, False if not found
        """
        self._cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        self.connection.commit()

        if self._cursor.rowcount > 0:
            self._clear_caches()
            return True
        return False

    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions from the database.

        This should be called periodically (e.g., via a background task)
        to prevent the database from growing indefinitely.

        Returns:
            int: Number of sessions deleted

        Example:
            >>> # Run cleanup every hour
            >>> deleted = manager.cleanup_expired_sessions()
            >>> print(f"Cleaned up {deleted} expired sessions")
        """
        cutoff_time = int(time.time()) - self.session_timeout
        self._cursor.execute(
            "DELETE FROM sessions WHERE last_active < ?",
            (cutoff_time,),
        )
        self.connection.commit()

        deleted = self._cursor.rowcount
        if deleted > 0:
            self._clear_caches()
            print(f"Cleaned up {deleted} expired sessions")

        return deleted

    def get_active_session_count(self) -> int:
        """
        Get the count of currently active (non-expired) sessions.

        Returns:
            int: Number of active sessions

        """
        cutoff_time = int(time.time()) - self.session_timeout
        self._cursor.execute(
            "SELECT COUNT(*) FROM sessions WHERE last_active >= ?",
            (cutoff_time,),
        )
        return self._cursor.fetchone()[0]

    def _get_user_sessions_impl(self, user_id: int) -> tuple:
        """
        Internal implementation for retrieving all active sessions for a user.

        Args:
            user_id: User's database ID

        Returns:
            tuple: Tuple of active session_ids for the user

        """
        cutoff_time = int(time.time()) - self.session_timeout
        self._cursor.execute(
            "SELECT session_id FROM sessions WHERE user_id = ? AND last_active >= ?",
            (user_id, cutoff_time),
        )
        # Return tuple for immutability and cache efficiency
        return tuple(row[0] for row in self._cursor.fetchall())

    def logout_all_user_sessions(self, user_id: int) -> int:
        """
        Logout all sessions for a user (e.g., on password change or account lock).

        Uses user_id to ensure we logout the correct user even if their
        username has changed.

        Args:
            user_id: User's database ID

        Returns:
            int: Number of sessions deleted
        """
        self._cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        self.connection.commit()

        count = self._cursor.rowcount
        if count > 0:
            self._clear_caches()
            print(f"Logged out {count} sessions for user_id {user_id}")

        return count

    def _clear_caches(self):
        """
        Clear all LRU caches in a single operation.

        This must be called after any database modification to ensure
        cached data doesn't become stale.
        """
        self.get_session.cache_clear()
        self.get_user_sessions.cache_clear()

    def close(self):
        """
        Close the database connection.

        Should be called on server shutdown to ensure all data is flushed
        and the database file is properly closed.
        """
        self.connection.close()
