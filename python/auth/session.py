"""
Session management utilities.

This module provides background session cleanup functionality.

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

import time
import utils.constants as c


def cleanup_sessions_loop() -> None:
    """
    Background loop that periodically removes expired user sessions.

    This function runs in a separate thread and continuously cleans up
    expired sessions every 60 seconds. It responds immediately to shutdown
    signals for server termination.

    The cleanup process:
    1. Calls SESSION_MANAGER.cleanup_expired_sessions()
    2. Waits 60 seconds (or until shutdown signal)
    3. Repeats until server shutdown
    """

    while not c.SERVER_STATE.should_shutdown():
        try:
            c.SESSION_MANAGER.cleanup_expired_sessions()
            # Use wait instead of sleep for faster shutdown response
            if c.SERVER_STATE.wait_for_shutdown(timeout=60):
                break
        except Exception as e:
            print(f"Session cleanup error: {e}")
            time.sleep(1)
