"""
Thread-safe server state manager.

This module provides a centralized, thread-safe mechanism for managing server
state and coordinating shutdown across multiple threads. It replaces global
variables and polling with proper event-based signaling.

Classes:
    ServerState: Thread-safe server state manager with event-based signaling

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

from typing import Optional
import threading


class ServerState:
    """
    Thread-safe server state manager with event-based shutdown signaling.

    This class provides a clean way to coordinate server lifecycle events
    across multiple threads without relying on global variables or polling.
    It uses threading.Event objects for efficient signaling and minimal
    CPU usage during wait operations.

    Key Features:
        - Thread-safe state management
        - Event-based signaling (no polling required)
        - Separate error and shutdown events
        - Optional timeout on shutdown waits

    Attributes:
        _shutdown_event: Event signaled when shutdown is requested
        _error_event: Event signaled when critical error occurs
        _lock: Lock protecting error_message access
        _error_message: String describing the error (if any)

    Example:
        >>> state = ServerState()
        >>>
        >>> # In worker thread
        >>> if state.should_shutdown():
        ...     return
        >>>
        >>> # In error handler
        >>> state.signal_error("Database connection lost")
        >>>
        >>> # In main thread
        >>> state.wait_for_shutdown(timeout=30)
    """

    __slots__ = ("_shutdown_event", "_error_event", "_lock", "_error_message")

    def __init__(self):
        """
        Initialize the server state manager.

        Creates shutdown and error events (both initially unset) and
        a lock for protecting error message access.
        """
        self._shutdown_event = threading.Event()
        self._error_event = threading.Event()
        self._lock = threading.Lock()
        self._error_message = None

    def signal_shutdown(self, reason: str = "Shutdown requested"):
        """
        Signal graceful shutdown to all waiting threads.

        This method is thread-safe and idempotent - multiple calls are safe.
        All threads waiting on should_shutdown() or wait_for_shutdown() will
        be immediately notified.

        Args:
            reason: Human-readable reason for shutdown (logged to console)

        """
        with self._lock:
            print(f"Shutdown signal: {reason}")
            self._shutdown_event.set()

    def signal_error(self, error_message: str):
        """
        Signal critical error and initiate shutdown.

        This method sets both error and shutdown events, ensuring the server
        stops while preserving the error information for logging or display.

        Args:
            error_message: Description of the error that occurred
        """
        with self._lock:
            self._error_message = error_message
            self._error_event.set()
            self._shutdown_event.set()  # Error implies shutdown
            print(f"ERROR: {error_message}")

    def should_shutdown(self) -> bool:
        """
        Check if shutdown has been requested.

        This is a non-blocking check that returns immediately. Use this in
        worker loops to periodically check if shutdown is needed.

        Returns:
            bool: True if shutdown requested, False otherwise
        """
        return self._shutdown_event.is_set()

    def has_error(self) -> bool:
        """
        Check if a critical error has occurred.

        This is useful for distinguishing between graceful shutdown and
        error-triggered shutdown.

        Returns:
            bool: True if error occurred, False otherwise
        """
        return self._error_event.is_set()

    def get_error_message(self) -> Optional[str]:
        """
        Get the error message if an error has occurred.

        This method is thread-safe and returns None if no error has occurred.

        Returns:
            str: Error message if error occurred
            None: If no error has occurred
        """
        with self._lock:
            return self._error_message

    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """
        Block until shutdown is signaled or timeout expires.

        This is an efficient blocking operation that uses minimal CPU while
        waiting. It's the recommended way to keep the main thread alive while
        worker threads handle requests.

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            bool: True if shutdown was signaled, False if timeout expired
        """
        return self._shutdown_event.wait(timeout)
