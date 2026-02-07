"""
HTTP and WebSocket request handler implementation.

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

import sys
import json
import socket
import struct
from http import server, cookies
import hashlib
import gzip
import io
import threading
import base64
import os
import time
from typing import Optional, Any, Dict
import mimetypes
from urllib.parse import parse_qs, unquote_plus


class NoDataException(Exception):
    """Raised when no data is read from HTML file."""


class WebSocketError(Exception):
    """Raised when WebSocket encounters an error."""


class NoLengthException(Exception):
    """Raised when no length can be read."""


class HandlerException(Exception):
    """Generic exception raised to cut down on error numbers"""


class DecodeException(Exception):
    """Exception thrown when an unsupported type is decoded"""


def read_exactly(rfile, n):
    """
    Helper function to read exactly n bytes from a file-like object.
    Raises WebSocketError if socket closes unexpectedly.

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    data = b""
    while len(data) < n:
        chunk = rfile.read(n - len(data))
        if not chunk:
            raise WebSocketError("Unexpected socket close")
        data += chunk
    return data


class ThreadedHandlerWithSockets(server.BaseHTTPRequestHandler):
    """HTTP request handler with WebSocket support."""

    _ws_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    _opcode_continu = 0x0
    _opcode_text = 0x1
    _opcode_binary = 0x2
    _opcode_close = 0x8
    _opcode_ping = 0x9
    _opcode_pong = 0xA

    mutex = threading.Lock()
    connected = False

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

        self.on_ws_connected()

        try:
            while True:
                # You'll need to implement frame parsing here
                def periodic_sender():
                    try:
                        while True:
                            self.send_message("Hello from server every 5 seconds")
                            time.sleep(5)
                    except Exception as e:
                        print(f"WebSocket closed or error occurred: {e}")

                threading.Thread(target=periodic_sender, daemon=True).start()
                if not self.connected:
                    break
        except WebSocketError:
            pass
        finally:
            self.on_ws_closed()

    def _read_messages(self):
        """Read and process WebSocket messages."""
        while self.connected:
            try:
                self._read_next_message()
            except (socket.error, WebSocketError) as e:
                # websocket content error, time-out or disconnect.
                self.log_error(f"RCV: Close connection: Socket Error {e.args}")
                self._ws_close()
            except Exception as err:
                # unexpected error in websocket connection.
                self.log_error(f"RCV: Exception: in _read_messages: {err.args}")
                self._ws_close()

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
            self._on_message(unmasked.decode("utf-8"))
        except (struct.error, TypeError) as e:
            # catch exceptions from ord() and struct.unpack()
            if self.connected:
                raise WebSocketError("Websocket read aborted while listening") from e
            # the socket was closed while waiting for input
            self.log_error("RCV: _read_next_message aborted after closed connection")
            print(e)

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
        self.end_headers()

        self.close_connection = False  # prevent auto-close
        self.connected = True

        self.on_ws_connected()  # must not block or crash

    def _ws_close(self):
        """Close WebSocket connection safely."""
        # avoid closing a single socket two time for send and receive.
        with self.mutex:
            if self.connected:
                self.connected = False
                # Terminate BaseHTTPRequestHandler.handle() loop:
                self.close_connection = True
                # send close and ignore exceptions. An error may already have occurred.
                try:
                    self._send_close()
                except Exception:
                    pass
                try:
                    self.on_ws_closed()
                except Exception:
                    pass

    def _send_close(self):
        """Send WebSocket close frame."""
        # Dedicated _send_close allows for catches
        msg = bytearray()
        msg.append(0x80 + self._opcode_close)
        msg.append(0x00)
        try:
            self.request.sendall(msg)
        except Exception:
            pass

    def _on_message(self, message):
        # PERFORM CUSTOM LOGIC HERE
        # call on_ws_message so subclass can implement behavior
        self.on_ws_message(message)

    def parse_out(self, data: str) -> Optional[dict]:
        """
        Parses a string of key-value pairs into a dictionary.

        The function splits the input string by the '&' character to extract
        individual key-value pairs, then further splits each pair by the '=' character
        to separate keys from values.

        Args:
            data (str): A string containing key-value pairs separated by '&' and '='.

        Returns:
            dict: A dictionary where keys and values are extracted from the input string.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            parsed = {}
            # Handle JSON data
            if data.strip().startswith("{"):
                return json.loads(data)

            # Handle form-encoded data
            for part in data.split("&"):
                if "=" in part:
                    key, value = part.split("=", 1)
                    parsed[key] = value
            return parsed
        except json.JSONDecodeError as f:
            # If JSON parsing fails, try form encoding
            try:
                parsed = {}
                for part in data.split("&"):
                    if "=" in part:
                        key, value = part.split("=", 1)
                        parsed[key] = value
                return parsed
            except (IndexError, ValueError, TypeError) as e:
                f.msg = f"Failed json decode and form encode {f.msg} - {e}"
                raise f from e
        except Exception as e:
            self.send_error(400, "FailedJsonParse", f"Error parsing data: {e}")
            return {}

    def write(self, data: bytes) -> None:
        """
        Writes the given data to the response stream (wfile).

        This method ensures that the data is sent to the client as part of the HTTP response.

        Args:
            data (bytes): The data to be written to the response stream.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        self.wfile.write(data)

    def end_headers_cache(self) -> None:
        """
        Sends cache control headers and ends headers.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        self.send_header("Cache-Control", "public, max-age=31536000")
        super().end_headers()

    def read_html(self, file: str) -> str:
        """
        Reads and returns the content of an HTML file.

        Args:
            file (str): The path to the HTML file to read.

        Returns:
            str: The content of the HTML file, or an empty string if an error occurs.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            # Open the file in read mode with UTF-8 encoding
            with open(file, "r", encoding="utf-8") as file_data:
                # Return the content of the file
                return file_data.read()
        except Exception:
            # Send error response if file reading fails
            self.send_error(422, "Error reading data from html file: {e}")
            return ""

    def serve_file(self) -> None:
        """
        Serve JavaScript, CSS, and other static files from the frontend directory.

        Now works with the new directory structure where frontend/ is a subdirectory.
        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            # Get the script directory (where server.py is located)
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            frontend_dir = os.path.join(script_dir, "frontend")

            # Remove leading slash and resolve path
            request_path = self.path.lstrip("/")

            # Build filepath relative to frontend directory
            filepath = os.path.join(frontend_dir, request_path)
            filepath = os.path.abspath(filepath)

            # Security: Prevent directory traversal
            if not filepath.startswith(frontend_dir):
                self.send_error(403, "Forbidden", "Access denied")
                return

            if os.path.exists(filepath) and os.path.isfile(filepath):
                self.send_response(200)

                # Determine content type
                content_type = "application/octet-stream"
                if filepath.endswith(".js"):
                    content_type = "application/javascript"
                elif filepath.endswith(".css"):
                    content_type = "text/css"
                elif filepath.endswith(".html"):
                    content_type = "text/html"
                elif filepath.endswith(".json"):
                    content_type = "application/json"
                elif filepath.endswith(".png"):
                    content_type = "image/png"
                elif filepath.endswith(".jpg") or filepath.endswith(".jpeg"):
                    content_type = "image/jpeg"
                elif filepath.endswith(".svg"):
                    content_type = "image/svg+xml"

                self.send_header("Content-Type", content_type)

                with open(filepath, "rb") as f:
                    data = f.read()

                # Compress text-based files
                if (
                    filepath.endswith(".js")
                    or filepath.endswith(".css")
                    or filepath.endswith(".html")
                ):
                    data = self.compress_gzip(data)

                if "non-static" in filepath:
                    self.end_headers()
                else:
                    self.end_headers_cache()
                self.write(data)
            else:
                self.send_error(404, "InvalidPath", f"File not found: {filepath}")
        except Exception as e:
            self.send_error(500, "FailedPathCheck", f"Error serving file: {e}")

    def compress_gzip(self, data: bytes) -> bytes:
        """
        Compresses the given data using gzip if the client accepts it.

        Args:
            data (bytes): The data to be compressed.

        Returns:
            bytes: The compressed data or the original data
                if the client does not accept gzip encoding.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        if not "gzip" in self.headers.get("Accept-Encoding", ""):
            return data
        self.send_header("Content-encoding", "gzip")
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb") as gzip_file:
            gzip_file.write(data)
        return buffer.getvalue()

    def serve_icons(self, icons_root: str = "icons") -> None:
        """
        Serves icons and favicon from the "icons" directory.

        Args:
            icons_root: Path to icons directory

        Returns:
            None

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            # Base icons directory (absolute, resolved once)
            icons_root = os.path.abspath(icons_root)

            # Strip query string + leading slash
            request_path = self.path.split("?", 1)[0].lstrip("/")

            # Remove "icons/" prefix if present
            if request_path.startswith("icons/"):
                request_path = request_path[6:]  # Remove exactly "icons/"

            filepath = os.path.join(icons_root, request_path)

            # Normalize to resolve any .. or .
            filepath = os.path.abspath(filepath)

            # Prevent directory traversal
            # Note: os.path.join already handles absolute icons_root, so we just need to check
            # that the final path is within icons_root
            if not (filepath.startswith(icons_root + os.sep) or filepath == icons_root):
                self.send_error(403, "Forbidden")
                return

            # Check if file exists
            if not os.path.isfile(filepath):
                self.send_error(404, f"File not found: {request_path}")
                return

            # Get file size
            size = os.path.getsize(filepath)
            if size == 0:
                self.send_error(500, "Empty file")
                return

            # Guess content type
            content_type, _ = mimetypes.guess_type(filepath)
            if content_type is None:
                content_type = "application/octet-stream"

            # Send headers
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(size))
            self.end_headers_cache()

            # Stream file in chunks to handle BrokenPipe gracefully
            try:
                with open(filepath, "rb") as f:
                    # Read and send in 8KB chunks
                    chunk_size = 8192
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            except BrokenPipeError:
                # Client closed connection - this is normal, don't report as error
                pass

        except BrokenPipeError:
            # Client closed connection during headers - ignore
            pass
        except Exception as e:
            # Only try to send error if connection is still alive
            try:
                self.send_error(500, f"Error serving file: {e}")
            except (BrokenPipeError, ConnectionResetError):
                # Connection dead, can't send error - just log it
                print(f"Error serving {self.path}: {e}", file=sys.stderr)

    def serve_page(
        self, page: str | bytes, response: int = 200, header: str = "text/html"
    ) -> None:
        """
        Serves the given page to the correct browser.
        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            self.send_response(response)
            self.send_header("Content-Type", header)

            if isinstance(page, bytes):
                data = self.compress_gzip(page)
            else:
                data = self.compress_gzip(page.encode("utf-8"))

            self.end_headers()
            self.write(data)
        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected — normal, ignore
            pass
        except UnicodeEncodeError as e:
            raise HandlerException(f"Encoding error: {e}") from e
        except ValueError as e:
            raise HandlerException(f"Header/value error: {e}") from e
        except OSError as e:
            raise HandlerException(f"Socket error: {e}") from e
        except Exception as e:
            raise HandlerException(f"Unhandled HTTP error: {e}") from e

    def redirect(self, page: str) -> None:
        """
        Redirects user to appropriate page.
        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        self.send_response(303)
        self.send_header("Location", page)
        self.end_headers()

    def json_response(
        self, data: dict, response_code: int = 200, compress: bool = False
    ) -> None:
        """
        Sends a JSON response to the client with proper headers.

        Args:
            data: Dictionary to be serialized as JSON
            response_code: HTTP response code (default: 200)
            compress: Whether to gzip compress the response (default: False)

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            json_data = json.dumps(data).encode("utf-8")

            self.send_response(response_code)
            self.send_header("Content-Type", "application/json")

            if compress and "gzip" in self.headers.get("Accept-Encoding", ""):
                self.send_header("Content-Encoding", "gzip")
                buffer = io.BytesIO()
                with gzip.GzipFile(fileobj=buffer, mode="wb") as gzip_file:
                    gzip_file.write(json_data)
                json_data = buffer.getvalue()

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
        ----------
        cookie_name : str
            The name of the cookie to retrieve.

        Returns
        -------
        dict
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
        try:
            length = self.headers.get("Content-Length")
            if not length:
                raise NoLengthException("Missing Content-Length header")

            length = int(length)
            raw = self.rfile.read(length).decode("utf-8")

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
        except NoLengthException as e:
            self.send_error(411, "ErrNoLen", str(e))
        except DecodeException as e:
            self.send_error(400, "ErrDecode", f"{e}")
        except Exception as e:
            self.send_error(400, "ErrRead", f"Failed to read POST data: {e}")

        return None
