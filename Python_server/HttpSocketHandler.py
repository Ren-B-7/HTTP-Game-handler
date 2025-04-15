import socket
import struct
import http.server
import secrets
import hashlib
import gzip
import http.cookies
import io
import threading
import base64
import os

class NoDataException(Exception):
    """
    Custom Exception to pass when no data is read from html file
    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """

    pass


class WebSocketError(Exception):
    """
    Custom Exception to pass when WebSocket throws an error
    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """

    pass



class ThreadedHandlerWithSockets(http.server.BaseHTTPRequestHandler):

    _ws_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    _opcode_continu = 0x0
    _opcode_text = 0x1
    _opcode_binary = 0x2
    _opcode_close = 0x8
    _opcode_ping = 0x9
    _opcode_pong = 0xA

    mutex = threading.Lock()

    def on_ws_message(self, message):
        """Override this handler to process incoming websocket messages."""
        pass

    def on_ws_connected(self):
        """Override this handler."""
        pass

    def on_ws_closed(self):
        """Override this handler."""
        pass

    def send_message(self, message):
        self._send_message(self._opcode_text, message)

    def finish(self):
        # needed when wfile is used
        try:
            super().finish()
        except (socket.error, TypeError) as err:
            self.log_message(
                "finish(): Exception: in BaseHTTPRequestHandler.finish(): %s"
                % str(err.args)
            )

    def _handle_websocket(self):
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            raise WebSocketError("Missing Sec-WebSocket-Key header")

        accept_val = base64.b64encode(
            hashlib.sha1((key + self._ws_GUID).encode()).digest()
        ).decode()

        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept_val)
        self.end_headers()

        self.on_ws_connected()

        try:
            while True:
                # You'll need to implement frame parsing here
                pass
        except WebSocketError:
            pass
        finally:
            self.on_ws_closed()

    def _read_messages(self):
        while self.connected == True:
            try:
                self._read_next_message()
            except (socket.error, WebSocketError) as e:
                # websocket content error, time-out or disconnect.
                self.log_message("RCV: Close connection: Socket Error %s" % str(e.args))
                self._ws_close()
            except Exception as err:
                # unexpected error in websocket connection.
                self.log_error("RCV: Exception: in _read_messages: %s" % str(err.args))
                self._ws_close()

    def _read_next_message(self):
        # self.rfile.read(n) is blocking.
        # it returns however immediately when the socket is closed.
        try:
            self.opcode = self.rfile.read(1)[0] & 0x0F
            self.opcode = self.rfile.read(1)[0] & 0x7F
            if length == 126:
                length = struct.unpack(">H", self.rfile.read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self.rfile.read(8))[0]
            masks = [byte for byte in self.rfile.read(4)]
            decoded = ""
            for char in self.rfile.read(length):
                decoded += chr(char ^ masks[len(decoded) % 4])
            self._on_message(decoded)
        except (struct.error, TypeError) as e:
            # catch exceptions from ord() and struct.unpack()
            if self.connected:
                raise WebSocketError("Websocket read aborted while listening")
            else:
                # the socket was closed while waiting for input
                self.log_error(
                    "RCV: _read_next_message aborted after closed connection"
                )
                pass

    def _send_message(self, opcode, message):
        try:
            # use of self.wfile.write gives socket exception after socket is closed. Avoid.
            self.request.send(chr(0x80 + opcode))
            length = len(message)
            if length <= 125:
                self.request.send(chr(length))
            elif length >= 126 and length <= 65535:
                self.request.send(chr(126))
                self.request.send(struct.pack(">H", length))
            else:
                self.request.send(chr(127))
                self.request.send(struct.pack(">Q", length))
            if length > 0:
                self.request.send(message)
        except socket.error as e:
            # websocket content error, time-out or disconnect.
            self.log_message("SND: Close connection: Socket Error %s" % str(e.args))
            self._ws_close()
        except Exception as err:
            # unexpected error in websocket connection.
            self.log_error("SND: Exception: in _send_message: %s" % str(err.args))
            self._ws_close()

    def _handshake(self):
        headers = self.headers
        if headers.get("Upgrade", None) != "websocket":
            return
        key = headers["Sec-WebSocket-Key"]
        digest = base64.b64encode(
            hashlib.sha1((key + self._ws_GUID).encode()).digest()
        ).decode()
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", str(digest))
        self.end_headers()
        self.connected = True
        # self.close_connection = 0
        self.on_ws_connected()

    def _ws_close(self):
        # avoid closing a single socket two time for send and receive.
        self.mutex.acquire()
        try:
            if self.connected:
                self.connected = False
                # Terminate BaseHTTPRequestHandler.handle() loop:
                self.close_connection = 1
                # send close and ignore exceptions. An error may already have occurred.
                try:
                    self._send_close()
                except:
                    pass
                self.on_ws_closed()
            else:
                self.log_message("_ws_close websocket in closed state. Ignore.")
                pass
        finally:
            self.mutex.release()

    def _on_message(self, message):
        # self.log_message("_on_message: opcode: %02X msg: %s" % (self.opcode, message))

        # close
        if self.opcode == self._opcode_close:
            self.connected = False
            # Terminate BaseHTTPRequestHandler.handle() loop:
            self.close_connection = 1
            try:
                self._send_close()
            except:
                pass
            self.on_ws_closed()
        # ping
        elif self.opcode == self._opcode_ping:
            _send_message(self._opcode_pong, message)
        # pong
        elif self.opcode == self._opcode_pong:
            pass
        # data
        elif (
            self.opcode == self._opcode_continu
            or self.opcode == self._opcode_text
            or self.opcode == self._opcode_binary
        ):
            self.on_ws_message(message)

    def _send_close(self):
        # Dedicated _send_close allows for catch all exception handling
        msg = bytearray()
        msg.append(0x80 + self._opcode_close)
        msg.append(0x00)
        self.request.send(msg)

    # Method to parse POST data into a dictionary of key-value pairs
    def write(self, data: bytes) -> None:
        """
        Override the write method to handle custom error handling.
        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            self.wfile.write(data)  # Call the base class method to write the data
        except BrokenPipeError:
            print(
                "Browser disconnected, path:",
                self.path,
                "user:",
                self.client_address[0],
            )
        except Exception as e:
            print(f"Error while writing to client: {e}")
            self.send_error(500, f"Error serving file: {e}")

    def end_headers(self) -> None:
        """
        Determines the file type to set headers properly.
        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        if self.path.endswith(".html"):
            self.send_header("Content-Type", "text/html")
        elif self.path.endswith(".js"):
            self.send_header("Content-Type", "application/javascript")
        elif self.path.endswith(".css"):
            self.send_header("Content-Type", "text/css")
        super().end_headers()

    def end_headers_cache(self) -> None:
        """
        Sets proper headers to cache the webpage, before setting header types for the files.
        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        self.send_header("Cache-Control", "public, max-age=31536000")
        self.end_headers()

    def parse_out(self, post_data: str) -> dict:
        """
        Parses the returned info from an http server.
        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            # Initialize an empty dictionary to store parsed data
            items = {}
            # Initialize variables to hold identifier and data
            identifier, data = None, None
            # Split the POST data by "&" and loop through each piece
            for data_pieces in post_data.split("&"):
                # Split each data piece into identifier and value
                data_pieces = data_pieces.strip().split("=")
                identifier = data_pieces[0]
                data = data_pieces[1] or ""
                # Ensure both identifier and data are present, raise exception if not
                if not (identifier):
                    raise Exception
                # Add the identifier and data to the dictionary
                items[identifier] = data
            return items
        except:
            # Send error response if parsing fails
            self.send_error(100, "Error reading data from webpage")
            return {}

    # Read an HTML file and return its content
    def read_html(self, file: str) -> str | None:
        """
        Reads the given html file and returns its content.
        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            # Open the file in read mode with UTF-8 encoding
            with open(file, "r", encoding="utf-8") as file_data:
                # Return the content of the file
                return file_data.read()
        except:
            # Send error response if file reading fails
            self.send_error(250, "Error reading data from html file")

    def serve_file(self) -> None:
        """
        Serve JavaScript, CSS, and other static files from the current directory.
        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            filepath = os.path.abspath(self.path.lstrip("/"))
            if os.path.exists(filepath) and os.path.isfile(filepath):
                self.send_response(200)
                data = open(filepath, "rb").read()
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
                self.send_error(404, f"File not found: {filepath}")
        except Exception as e:
            self.send_error(500, f"Error serving file: {e}")

    def compress_gzip(self, data: bytes) -> bytes:
        """
        Compresses the given data using gzip if the client accepts it.

        Args:
            data (bytes): The data to be compressed.

        Returns:
            bytes: The compressed data or the original data if the client does not accept gzip encoding.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        if not "gzip" in self.headers.get("Accept-Encoding", ""):
            return data
        self.send_header("Content-encoding", "gzip")
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb") as gzip_file:
            gzip_file.write(data)
        return buffer.getvalue()

    def serve_icons(self) -> None:
        """
        Serves icons and favicon from the "icons" directory.

        Args:
            None

        Returns:
            None

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            filepath = os.path.abspath("icons/" + self.path.lstrip("/"))
            if os.path.exists(filepath) and os.path.isfile(filepath):
                self.send_response(200)
                data = open(filepath, "rb").read()
                content_type = "image/png"
                if filepath.endswith(".ico"):
                    content_type = "image/x-icon"
                elif filepath.endswith(".svg"):
                    content_type = "image/svg+xml"
                elif filepath.endswith(".webmanifest"):
                    content_type = "application/manifest+json"

                self.send_header("Content-Type", content_type)
                self.end_headers_cache()
                self.write(data)
            else:
                self.send_error(404, f"File not found: {filepath}")
        except Exception as e:
            self.send_error(500, f"Error serving file: {e}")

    def serve_page(
        self, page: str | bytes, response: int = 200, header: str = "text/html"
    ) -> None:
        """
        Serves the given page to the correct browser.
        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            self.send_response(response)
            self.send_header("Content-type", header)
            if isinstance(page, bytes):
                data = self.compress_gzip(page)
            else:
                data = self.compress_gzip(page.encode("utf-8"))
            self.end_headers()
            # Write the content of the login page to the response
            self.write(data)
        except Exception as e:
            raise e

    def redirect(self, page: str) -> None:
        """
        Redirects user to appropriate page.
        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        self.send_response(303)
        self.send_header("Location", page)
        self.end_headers()

    def get_cookie(self, cookie_name) -> str:
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

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return {}
        cookies = http.cookies.SimpleCookie(cookie_header)
        return cookies.get(cookie_name) if cookie_name in cookies else None

    def read_post_request(self) -> dict:
        """
        Reads and parses a POST request to extract form data into a dictionary.

        This function reads the 'Content-Length' header to determine the size of the
        incoming POST data, reads and decodes the data, and then parses it into a dictionary
        using the `parse_out` method. If an error occurs during reading or parsing, it sends
        an error response and exits on critical failure.

        Returns:
            dict: Parsed form data as a dictionary.

        Raises:
            AssertionError: If the 'Content-Length' header is not an integer.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """

        try:
            length = int(self.headers.get("Content-Length"))
            assert isinstance(length, int), "length must be of type int"
            post_data = self.rfile.read(length).decode("utf-8")

            if not post_data:
                raise NoDataException("No data to read from html page")
            return self.parse_out(post_data)
        except NoDataException as e:
            print(e)
            return {}
        except:
            self.send_error(101, "Error reading data from webpage")
            exit(1)  # Exit on critical error
