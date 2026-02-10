"""
HTTP and WebSocket request handler implementation. Meant to be used with
TimeoutThreadingHTTPserver, but can be used with any http class.

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

import json
import socket
import struct
from http import server, cookies
import hashlib
import gzip
import threading
import base64
import time
from typing import Optional, Any, Dict
import mimetypes
from urllib.parse import parse_qs
from pathlib import Path
import uuid

from utils.constants import COMPRESSION_CACHE, ICONS_DIRECTORY, MAX_POST_SIZE
from utils.exceptions import (
    WebSocketError,
    LengthException,
    DecodeException,
)


def read_exactly(rfile, n):
    """
    Helper function to read exactly n bytes from a file-like object.
    Raises WebSocketError if socket closes unexpectedly.

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    data = b""
    if len(data) > n:
        raise LengthException("More data is looked for than specified")
    while len(data) < n:
        chunk = rfile.read(n - len(data))
        if not chunk:
            raise LengthException("Length is less than expected")
        data += chunk
    return data


class ThreadedHandlerWithSockets(server.SimpleHTTPRequestHandler):
    """HTTP request handler with WebSocket support."""

    _ws_GUID = str(uuid.uuid4())
    _opcode_continu = 0x0
    _opcode_text = 0x1
    _opcode_binary = 0x2
    _opcode_close = 0x8
    _opcode_ping = 0x9
    _opcode_pong = 0xA

    mutex = threading.Lock()

    def do_HEAD(self):
        self.do_GET()

    def _body_allowed(self) -> bool:
        return self.command != "HEAD"

    def handle(self) -> None:
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as e:
            print(f"Error caught: {e}")

    def on_ws_message(self, message):
        """
        Override this handler to process incoming websocket messages.

        Args:
            message: The incoming WebSocket message to process

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        # Default implementation - subclasses should override

    def on_ws_connected(self):
        """Override this handler to handle WebSocket connection."""
        self.log_message("Player connected from %s", self.address_string())

    def on_ws_closed(self):
        """Override this handler to handle WebSocket closure."""
        self.log_message("Player disconnected from %s", self.address_string())

    def send_message(self, message):
        if isinstance(message, str):
            message = message.encode("utf-8")
        self._send_message(self._opcode_text, message)

    def finish(self):
        # needed when wfile is used
        try:
            super().finish()
        except (socket.error, TypeError) as err:
            self.log_error(
                f"finish(): Exception: in BaseHTTPRequestHandler.finish(): {err.args}"
            )

    def _handle_websocket(self):
        self._handshake()

        sender = threading.Thread(target=self._periodic_sender, daemon=True)
        sender.start()
        try:
            self._read_messages()
        finally:
            self._ws_close()

    def _periodic_sender(self):
        while self.connected:
            self.send_message("Hello from server every 5 seconds")
            time.sleep(5)

    def _read_messages(self):
        """Read and process WebSocket messages."""
        while self.connected:
            if self.server and self.server.last_activity_time:
                self.server.last_activity_time = time.time()
            try:
                self._read_next_message()
            except (socket.error, WebSocketError) as e:
                # websocket content error, time-out or disconnect.
                self.log_error(f"RCV: Close connection: Socket Error {e.args}")
            except Exception as err:
                # unexpected error in websocket connection.
                self.log_error(f"RCV: Exception: in _read_messages: {err.args}")

    def _read_next_message(self):
        """Read the next WebSocket message from the client."""
        # self.rfile.read(n) is blocking.
        # it returns however immediately when the socket is closed.
        try:
            first_byte = read_exactly(self.rfile, 1)[0]
            second_byte = read_exactly(self.rfile, 1)[0]

            _fin = (first_byte >> 7) & 1
            self.opcode = first_byte & 0x0F
            _masked = (second_byte >> 7) & 1

            length = second_byte & 0x7F
            match length:
                case 126:
                    length = struct.unpack(">H", read_exactly(self.rfile, 2))[0]
                case 127:
                    length = struct.unpack(">Q", read_exactly(self.rfile, 8))[0]

            if (second_byte >> 7) & 1:
                try:
                    masks = read_exactly(self.rfile, 4)
                except Exception as e:
                    raise WebSocketError(
                        "Websocket read aborted while listening"
                    ) from e
            else:
                raise WebSocketError("Frames must be masked")

            masked_data = read_exactly(self.rfile, length)

            unmasked = bytearray(b ^ masks[i % 4] for i, b in enumerate(masked_data))
            if self.opcode == self._opcode_ping:
                self._send_message(self._opcode_pong, unmasked)
                return

            if self.opcode == self._opcode_pong:
                return

            if self.opcode == self._opcode_close:
                self._ws_close()
                return

            if self.opcode == self._opcode_text:
                self._on_message(unmasked.decode("utf-8"))
        except (struct.error, TypeError) as e:
            # catch exceptions from ord() and struct.unpack()
            if self.connected:
                raise WebSocketError("Websocket read aborted while listening") from e
            # the socket was closed while waiting for input
            self.log_error("RCV: _read_next_message aborted after closed connection")

    def _send_message(self, opcode, message):
        try:
            frame = bytearray()
            frame.append(0x80 | opcode)  # FIN + opcode

            length = len(message)
            if length <= 125:
                frame.append(length)
            elif length <= 65535:
                frame.append(126)
                frame.extend(struct.pack(">H", length))
            else:
                frame.append(127)
                frame.extend(struct.pack(">Q", length))

            frame.extend(message)

            self.request.sendall(frame)
        except socket.error as e:
            self.log_error(f"SND: Close connection: Socket Error {e.args}")
            self._ws_close()
        except Exception as err:
            self.log_error(f"SND: Exception: in _send_message: {err.args}")
            self._ws_close()

    def _handshake(self):
        if self.headers.get("Upgrade", "").lower() != "websocket":
            self.send_error(400, "Invalid Upgrade header")
            return
        if "upgrade" not in self.headers.get("Connection", "").lower():
            self.send_error(400, "Invalid Connection header")
            return

        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            self.send_error(400, "Missing Sec-WebSocket-Key")
            return

        accept = base64.b64encode(
            hashlib.sha1((key + self._ws_GUID).encode()).digest()
        ).decode()

        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        super().end_headers()

        self.connected = True
        self.on_ws_connected()

    def _ws_close(self):
        # avoid closing the socket twice
        if not self.connected:
            return
        self.connected = False
        self.on_ws_closed()
        try:
            self._send_message(self._opcode_close, b"")
        except socket.error:
            pass
        except Exception as err:
            self.log_error(f"_ws_close(): Exception: {err.args}")

    def _on_message(self, message):
        try:
            self.on_ws_message(message)
        except Exception as e:
            self.log_error(f"on_ws_message(): Exception: {e}")

    def write(self, data: bytes) -> None:
        """
        Wrapper around wfile.write to safely handle disconnects and suppress logs.
        Ensures body is only sent if allowed (honors HEAD requests).

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        if self._body_allowed():
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # Client disconnected (normal, not an error)
                pass

    def send_headers_cache(self) -> None:
        """
        Sends headers to notify of a cached object.
        Used for static assets (JS, CSS, images) that rarely change.
        Warning: Only use for versioned or immutable files!

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")

    def send_headers_security(self) -> None:
        """
        Used to include extra security headers.
        Used for html pages that are non-static mostly those that should not be
        cached

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "font-src 'self' data:; connect-src 'self' ws: wss:;",
        )
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()",
        )

    def serve_file(
        self,
        file: Path | bytes,
        *,
        content_type: str | None = None,
        response_code: int = 200,
        cache: bool = False,
        compress: bool = True,
    ) -> None:
        try:
            file_path: Path | None = None

            # Read data
            if isinstance(file, Path):
                file_path = file.resolve()

                if not file_path.exists() or not file_path.is_file():
                    self.send_error(404, "File not found")
                    return

                data = file_path.read_bytes()
            else:
                data = file

            # Determine content type
            if content_type is None:
                if file_path is not None:
                    content_type, _ = mimetypes.guess_type(str(file_path))
                else:
                    content_type = "application/octet-stream"

            content_type = content_type or "application/octet-stream"
            is_html = content_type.startswith("text/html")

            # Response
            self.send_response(response_code)
            self.send_header("Content-Type", content_type)

            # Compression
            if compress:
                data = self.compress_gzip(
                    data,
                    compresslevel=6,
                    cache_key=str(file_path) if file_path else None,
                )
            else:
                self.send_header("Content-Length", str(len(data)))

            # HTML always gets security headers
            if is_html:
                self.send_headers_security()

            # Cache policy is non deterministic
            if cache:
                self.send_headers_cache()

            super().end_headers()
            self.write(data)

        except BrokenPipeError:
            pass
        except Exception as e:
            self.send_error(500, "ServeFileError", str(e))

    def compress_gzip(
        self, data: bytes | str, compresslevel: int = 6, cache_key: Optional[str] = None
    ) -> bytes:
        """
        Compresses data using cached compressor (multicore-equivalent performance).

        Features:
        - Caches compressed files for instant repeat serving
        - Uses optimized gzip.compress() (3x faster than GzipFile)
        - Non-blocking (cache lookups are instant)

        Args:
            data: Data to compress
            compresslevel: Compression level (1-9), default 6
            cache_key: Cache key for this data (e.g., filepath)

        Returns:
            Compressed data

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        if isinstance(data, str):
            data = data.encode("utf-8")
        if "gzip" not in self.headers.get("Accept-Encoding", ""):
            return data

        # Use cached compression (instant on cache hit)
        compressed = COMPRESSION_CACHE.compress(
            data, compresslevel=compresslevel, cache_key=cache_key
        )

        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(compressed)))
        return compressed

    def serve_icons(self, icons_root: Path = ICONS_DIRECTORY) -> None:
        """
        Serve icons via the generic static file handler.
        """
        request_path = self.path.split("?", 1)[0].lstrip("/")

        # Strip `icons/` prefix if present
        if request_path.startswith("icons/"):
            request_path = request_path[6:]

        self.serve_file(
            file=Path.joinpath(icons_root, request_path),
            cache=True,
            compress=False,  # images should not be gzipped
        )

    def serve_page(
        self,
        page: str | bytes | Path,
        response: int = 200,
        cache: bool = False,
        compress: bool = True,
    ) -> None:
        page = page.encode("utf-8") if isinstance(page, str) else page
        self.serve_file(
            file=page,
            content_type="text/html",
            response_code=response,
            cache=cache,
            compress=compress,
        )

    def redirect(self, path: str) -> None:
        """
        Redirects user to appropriate page.
        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        self.send_response(303)
        self.send_header("Location", path)
        self.send_header("Content-Length", "0")
        super().end_headers()

    def json_response(
        self, data: dict, response_code: int = 200, compress: bool = False
    ) -> None:
        """
        Sends JSON response with optional compression.

        NOTE: Does NOT use compression pool (JSON responses are small and fast).
        Uses direct gzip.compress() with level 1 for speed.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            json_data = json.dumps(data).encode("utf-8")

            self.send_response(response_code)
            self.send_header("Content-Type", "application/json")

            if compress and "gzip" in self.headers.get("Accept-Encoding", ""):
                # Fast compression (level 1) for real-time JSON responses
                json_data = gzip.compress(json_data, compresslevel=1)
                self.send_header("Content-Encoding", "gzip")

            self.send_header("Content-Length", str(len(json_data)))
            super().end_headers()
            self.wfile.write(json_data)
        except Exception as e:
            self.log_error(f"Error sending json response: {e}")
            self.send_error(500, "Internal server error")

    def json_error(self, message: str, code: int = 400) -> None:
        """
        Sends a JSON error response.

        Args:
            message: Error message to send
            code: HTTP error code (default: 400)

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        self.log_error(f"{message}: {code}")
        self.json_response({"success": False, "message": message}, code)

    def json_success(
        self, data: Optional[Dict[str, Any]] = None, message: Optional[str] = None
    ) -> None:
        response: Dict[str, Any] = {"success": True}

        if message is not None:
            response["message"] = message

        if data is not None:
            response.update(data)

        self.json_response(response, 200)

    def get_cookie(self, cookie_name) -> Optional[str]:
        """
        Get a cookie value by name.

        Parameters
        cookie_name : str
            The name of the cookie to retrieve.

        Returns
            A dictionary with a single key-value pair containing the cookie value.
            If the cookie does not exist, an empty dictionary is returned.

            dict{session id, username}

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return None
        cookies_bin = cookies.SimpleCookie(cookie_header)
        cookie = cookies_bin.get(cookie_name)
        return cookie.value if cookie else None

    def read_post_request(self) -> Optional[dict]:
        """
        Reads the wanted post request and returns a python object of it.
        Checks that the size is correct. And check that the size isnt exceeding
        the max or larger than the header specified

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            length = self.headers.get("Content-Length")
            if not length:
                raise LengthException("Missing Content-Length header")

            length = int(length)

            if length > MAX_POST_SIZE:
                raise LengthException("Post request too large")

            raw = read_exactly(self.rfile, length).decode("utf-8")

            content_type = self.headers.get("Content-Type", "")

            # JSON
            if content_type.startswith("application/json"):
                data = json.loads(raw)
                return {
                    k: v.strip() if isinstance(v, str) else v for k, v in data.items()
                }

            # Form encoded
            if content_type.startswith("application/x-www-form-urlencoded"):
                parsed = parse_qs(raw, keep_blank_values=True)
                return {k: v[0].strip() for k, v in parsed.items()}

            raise DecodeException("Unsupported Content-Type", 415)

        except json.JSONDecodeError:
            self.send_error(400, "ErrJSON", "Invalid JSON payload")
        except LengthException as e:
            self.send_error(411, "ErrLen", str(e))
        except DecodeException as e:
            self.send_error(400, "ErrDecode", f"{e}")
        except Exception as e:
            self.send_error(400, "ErrRead", f"Failed to read POST data: {e}")

        return None
