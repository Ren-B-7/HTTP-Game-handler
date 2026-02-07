"""
Custom exceptions for the Chess server.

This module defines all custom exception classes used throughout the server
to handle specific error conditions.
"""


class InactivityTimeoutException(Exception):
    """Custom exception to signal server inactivity timeout."""


class MajorServerSideException(Exception):
    """Custom exception to signal extreme cli game fault."""


class DBException(Exception):
    """Any DB error should be called via this"""


class ProcessingError(Exception):
    """Any Error that should be sent back to the connected user instance"""

    def __init__(self, message, code=400):
        self.code = code
        self.message = message
        # Call the base class constructor with the message
        super().__init__(self.message)

    def __str__(self):
        """Return a string representation including the code."""
        return f"[{self.code}] {self.message}"
