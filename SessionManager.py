"""
Efficient Session Manager using SQLite with LRU caching.

Memory efficient: Only active sessions cached, database holds all
Modified to use user_id for all critical operations instead of username
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
    Uses user_id as the primary identifier for all operations.

    Benefits:
    - Persistent sessions (survive server restart)
    - Bounded memory usage (LRU cache)
    - Fast lookup for active users
    - Automatic cleanup of expired sessions
    - Safe handling of username changes (uses immutable user_id)
    """

    __slots__ = ('db_path', 'session_timeout', 'max_cache_size', 'connection', 
                 'get_session', 'get_user_sessions', '_cursor')

    def __init__(
        self,
        db_path: Path,
        session_timeout: int = 600,
        max_cache_size: int = 1000,
        max_user_session_cache: int = 250,
    ):
        """
        Initialize session manager.

        Args:
            db_path: Path to SQLite database
            session_timeout: Session timeout in seconds (default: 10 minutes)
            max_cache_size: Maximum sessions to cache in memory (default: 1000)
            max_user_session_cache: Maximum user session queries to cache (default: 250)
        """
        self.db_path = db_path
        self.session_timeout = session_timeout
        self.max_cache_size = max_cache_size
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self._cursor = self.connection.cursor()

        # Create the cached method with the correct max_cache_size
        self.get_session = lru_cache(maxsize=max_cache_size)(self._get_session_impl)
        self.get_user_sessions = lru_cache(maxsize=max_user_session_cache)(
            self._get_user_sessions_impl
        )

        self._create_table()

    def _create_table(self):
        """Create sessions table if it doesn't exist."""
        # Use single execute for all schema creation
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
        Create a new session.

        Args:
            user_id: User's database ID (immutable)
            username: Username (mutable, for display only)
            ip: User's IP address

        Returns:
            session_id: Unique session identifier
        """
        session_id = secrets.token_hex(32)  # 64 character hex string
        now = int(time.time())

        self._cursor.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, user_id, username, ip, now, now),
        )
        self.connection.commit()

        # Single cache clear for both
        self._clear_caches()

        return session_id

    def _get_session_impl(self, session_id: str) -> Optional[Dict]:
        """
        Get session data implementation (cached).

        Args:
            session_id: Session identifier

        Returns:
            Session dict or None if not found/expired
        """
        self._cursor.execute(
            "SELECT user_id, username, ip, last_active FROM sessions WHERE session_id = ?",
            (session_id,),
        )

        row = self._cursor.fetchone()
        if not row:
            return None

        user_id, username, ip, last_active = row

        # Check if expired
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
        Update last_active timestamp.

        Args:
            session_id: Session identifier

        Returns:
            True if updated, False if session not found
        """
        self._cursor.execute(
            "UPDATE sessions SET last_active = ? WHERE session_id = ?",
            (int(time.time()), session_id),
        )
        self.connection.commit()

        # Only clear if actually updated
        if self._cursor.rowcount > 0:
            self._clear_caches()
            return True
        return False

    def update_username_in_sessions(self, user_id: int, new_username: str) -> int:
        """
        Update username in all sessions for a user (when username changes).
        Uses user_id to find sessions, ensuring we update the right user even if
        username was changed.

        Args:
            user_id: User's database ID (immutable identifier)
            new_username: New username to set

        Returns:
            Number of sessions updated
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
        Delete a session (logout).

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        self._cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        self.connection.commit()

        if self._cursor.rowcount > 0:
            self._clear_caches()
            return True
        return False

    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions.

        Returns:
            Number of sessions deleted
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
        """Get count of non-expired sessions."""
        cutoff_time = int(time.time()) - self.session_timeout
        self._cursor.execute(
            "SELECT COUNT(*) FROM sessions WHERE last_active >= ?",
            (cutoff_time,),
        )
        return self._cursor.fetchone()[0]

    def _get_user_sessions_impl(self, user_id: int) -> tuple:
        """
        Get all active sessions for a user by user_id (for multi-device support).
        Uses user_id instead of username to ensure correct user is found even
        after username changes.

        Args:
            user_id: User's database ID

        Returns:
            Tuple of session_ids
        """
        cutoff_time = int(time.time()) - self.session_timeout
        self._cursor.execute(
            "SELECT session_id FROM sessions WHERE user_id = ? AND last_active >= ?",
            (user_id, cutoff_time),
        )
        return tuple(row[0] for row in self._cursor.fetchall())

    def logout_all_user_sessions(self, user_id: int) -> int:
        """
        Logout all sessions for a user by user_id.
        Uses user_id instead of username to ensure we logout the correct user
        even if their username has changed.

        Args:
            user_id: User's database ID

        Returns:
            Number of sessions deleted
        """
        self._cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        self.connection.commit()

        count = self._cursor.rowcount
        if count > 0:
            self._clear_caches()
            print(f"Logged out {count} sessions for user_id {user_id}")

        return count

    def _clear_caches(self):
        """Clear both caches in a single operation."""
        self.get_session.cache_clear()
        self.get_user_sessions.cache_clear()

    def close(self):
        """Close database connection."""
        self.connection.close()
