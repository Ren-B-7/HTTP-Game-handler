from typing import Optional
import threading


class ServerState:
    """
    Thread-safe server state manager.
    Replaces the ERROR_FOUND global variable with proper event-based signaling.
    """

    __slots__ = ('_shutdown_event', '_error_event', '_lock', '_error_message')

    def __init__(self):
        self._shutdown_event = threading.Event()
        self._error_event = threading.Event()
        self._lock = threading.Lock()
        self._error_message = None

    def signal_shutdown(self, reason: str = "Shutdown requested"):
        """Signal graceful shutdown."""
        with self._lock:
            print(f"Shutdown signal: {reason}")
            self._shutdown_event.set()

    def signal_error(self, error_message: str):
        """Signal critical error."""
        with self._lock:
            self._error_message = error_message
            self._error_event.set()
            self._shutdown_event.set()
            print(f"ERROR: {error_message}")

    def should_shutdown(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_event.is_set()

    def has_error(self) -> bool:
        """Check if error occurred."""
        return self._error_event.is_set()

    def get_error_message(self) -> Optional[str]:
        """Get error message if any."""
        with self._lock:
            return self._error_message

    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """Wait for shutdown signal with optional timeout."""
        return self._shutdown_event.wait(timeout)
