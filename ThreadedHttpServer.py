"""
HTTP server with timeout capabilities and fast shutdown.

Improvements:
- Uses threading.Event for immediate shutdown response (vs 5 second polling)
- Cleaner timeout monitoring
- Better exception handling

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

from http.server import ThreadingHTTPServer
import threading
import time


class MajorThreadedHttpServerException(Exception):
    """ThreadingHTTPServer has encountered a major server side exception."""


class TimeoutThreadingHTTPServer(ThreadingHTTPServer):
    """HTTP server with configurable inactivity timeout and fast shutdown."""

    __slots__ = ('inactivity_timeout', 'stopping', 'timeout', 'last_activity_time',
                 '_stop_event', '_check_interval')

    def __init__(self, server_address, RequestHandlerClass, timeout_seconds=300):
        try:
            self._stop_event = threading.Event()
            self.stopping = False
            self.timeout = False
            self.inactivity_timeout = timeout_seconds
            self.last_activity_time = time.time()
            
            # Pre-calculate check interval (max 60 seconds)
            self._check_interval = min(60, timeout_seconds / 5)

            super().__init__(server_address, RequestHandlerClass)

        except Exception as e:
            raise MajorThreadedHttpServerException(
                f"Unable to initiate server class: {e}"
            ) from e

    def server_activate(self) -> None:
        """
        Starts the server and spawns a separate thread to monitor inactivity.
        Uses threading.Event for immediate shutdown response.
        """
        try:
            super().server_activate()
            self.last_activity_time = time.time()
            threading.Thread(target=self._monitor_inactivity, daemon=True).start()
        except Exception as e:
            raise MajorThreadedHttpServerException(
                f"Unable to start server: {e}"
            ) from e

    def process_request(self, request, client_address) -> None:
        """
        Processes an incoming request and updates the last activity timestamp.

        This method is called to handle each incoming request to the server. It
        updates the last_activity_time to the current time to indicate that there
        has been recent activity, and then delegates the actual processing of the
        request to the parent class's process_request method.

        Parameters:
            request: The incoming request to be processed.
            client_address: The address of the client making the request.
        """
        try:
            self.last_activity_time = time.time()
            super().process_request(request, client_address)
        except Exception as e:
            print(f"Error processing request from {client_address}: {e}")
            # Don't raise - allow server to continue

    def _monitor_inactivity(self) -> None:
        """
        Monitors server inactivity and shuts it down if idle for too long.

        Improved version using Event.wait() for immediate shutdown response
        instead of polling every 5 seconds.
        """
        try:
            while not self._stop_event.is_set():
                idle_time = time.time() - self.last_activity_time
                remaining_time = self.inactivity_timeout - idle_time

                if remaining_time <= 0:
                    print(
                        f"No activity for {self.inactivity_timeout / 60:.1f} minutes, "
                        f"shutting down server."
                    )
                    self.timeout = True
                    self.shutdown()
                    return

                # Sleep until timeout or stop signal (use pre-calculated interval)
                self._stop_event.wait(timeout=min(self._check_interval, remaining_time))

        except Exception as e:
            print(f"Error in inactivity monitor: {e}")

    def shutdown(self) -> None:
        if self.stopping:
            return
        self.stopping = True
        self._stop_event.set()
        super().shutdown()

    def server_close(self) -> None:
        """
        Close the server and ensure monitor thread stops.
        """
        self._stop_event.set()
        self.stopping = True
        super().server_close()
