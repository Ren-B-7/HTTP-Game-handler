"""
Custom exceptions for the Chess server.

Exception Hierarchy:
    - InactivityTimeoutException: Server timeout due to inactivity
    - MajorServerSideException: Critical game engine errors
    - DBException: Database operation failures
    - ProcessingError: Client-facing errors with HTTP codes
    - MajorThreadedHttpServerException: HTTP server initialization errors
    - NoDataException: Missing data in file reads
    - WebSocketError: WebSocket connection errors
    - LengthException: Missing or invalid length headers
    - HandlerException: Generic handler errors
    - DecodeException: Data decoding/deserialization errors
    - InstanceInoperable: Engine instance throws an error

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""


class InactivityTimeoutException(Exception):
    """
    Raised when server has been inactive for too long.

    This signals that the server should perform a graceful shutdown due to
    no client activity within the configured timeout period.

    Example:
        >>> if idle_time > timeout:
        ...     raise InactivityTimeoutException("No activity for 5 minutes")
    """


class MajorServerSideException(Exception):
    """
    Raised when the game engine encounters a critical fault.

    This indicates a serious issue with the game engine that prevents it
    from continuing to process games. The server should log this error
    and potentially restart the engine instance.

    Example:
        >>> if engine_process.returncode != 0:
        ...     raise MajorServerSideException("Game engine crashed")
    """


class DBException(Exception):
    """
    Raised for any database-related error.

    This is a catch-all for database operations that fail, including
    connection errors, query errors, and data integrity issues.

    Example:
        >>> try:
        ...     cursor.execute(query)
        ... except sqlite3.Error as e:
        ...     raise DBException(f"Database error: {e}") from e
    """


class ProcessingError(Exception):
    """
    Raised for errors that should be communicated back to the client.

    This exception includes both an HTTP status code and a user-friendly
    error message. It's used for validation errors, authentication failures,
    and other client-facing errors.

    Attributes:
        code (int): HTTP status code (default: 400)
        message (str): User-friendly error message

    Example:
        >>> if not valid_username(username):
        ...     raise ProcessingError("Invalid username format", code=400)
        >>>
        >>> if not authenticated:
        ...     raise ProcessingError("Authentication required", code=401)
    """

    def __init__(self, message: str, code: int = 400):
        """
        Initialize a processing error.

        Args:
            message: User-friendly error message
            code: HTTP status code (default: 400 Bad Request)
        """
        self.code = code
        self.message = message
        # Call the base class constructor with the message
        super().__init__(self.message)

    def __str__(self):
        """
        Return a string representation including the HTTP code.

        Returns:
            str: Formatted as "[CODE] message"

        Example:
            >>> str(ProcessingError("Bad input", 400))
            '[400] Bad input'
        """
        return f"[{self.code}] {self.message}"


class MajorThreadedHttpServerException(Exception):
    """
    Raised when the HTTP server encounters a critical initialization error.

    This indicates the server cannot start or bind to the requested port.
    This is typically unrecoverable and should cause the application to exit.

    Example:
        >>> try:
        ...     server = HTTPServer(('localhost', 80))
        ... except OSError as e:
        ...     raise MajorThreadedHttpServerException(
        ...         "Cannot bind to port 80: permission denied"
        ...     ) from e
    """


class NoDataException(Exception):
    """
    Raised when no data can be read from an expected source.

    This typically occurs when reading HTML files or other resources that
    should contain data but are empty or inaccessible.

    Example:
        >>> if not html_content:
        ...     raise NoDataException("HTML file is empty")
    """


class WebSocketError(Exception):
    """
    Raised when WebSocket connection encounters an error.

    This covers WebSocket handshake failures, protocol errors, and
    connection issues.

    Example:
        >>> if not valid_websocket_key:
        ...     raise WebSocketError("Invalid WebSocket key in handshake")
    """


class LengthException(Exception):
    """
    Raised when content length cannot be determined or is invalid.

    This is used when reading HTTP requests or responses that should have
    a Content-Length header but it's missing or malformed.

    Example:
        >>> if 'Content-Length' not in headers:
        ...     raise LengthException("Missing Content-Length header")
    """


class HandlerException(Exception):
    """
    Generic exception for HTTP request handler errors.

    This is a catch-all for various handler-level errors that don't fit
    into more specific categories. It helps reduce the number of exception
    types while still providing meaningful error information.

    Example:
        >>> if unsupported_http_method:
        ...     raise HandlerException("Method not allowed")
    """


class DecodeException(Exception):
    """
    Raised when data cannot be decoded or deserialized.

    This typically occurs when attempting to parse JSON, decode base64,
    or deserialize other data formats that turn out to be malformed.

    Example:
        >>> try:
        ...     data = json.loads(raw_data)
        ... except json.JSONDecodeError as e:
        ...     raise DecodeException("Invalid JSON") from e
    """


class InstanceInoperable(Exception):
    """Raised when an engine instance becomes unresponsive or crashes."""
