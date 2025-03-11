import datetime
import gzip
import hashlib
import http.server
import http.cookies
import io
import json
import os
import queue
import random
import secrets
import select
import signal
import sqlite3
import subprocess
import sys
import threading
import time

os.chdir(os.path.dirname(__file__))
os.chdir("../frontend")

game_cli = ""
bot_cli = ""

timeout = False
error_found = False
ending_server = False

promiscuis_ips = set()
player_session_store = {}
active_games = (
    {}
)  # 'session_id' = {'player1': p1, 'player2':p2, 'last_update': time.time(), 'game_data' = {} json passed from game}


db_connection = None
db_cursor = None
db_command_hook = queue.Queue()

thread_queue = queue.Queue()
instance_count = 0

LOGIN_HTML = os.path.abspath("login.html")
REGISTER_HTML = os.path.abspath("register.html")
GAME_HTML = os.path.abspath("game.html")
STATS_HTML = os.path.abspath("stats.html")
HOME_HTML = os.path.abspath("stats.html")

icons = [
    "/apple-touch-icon.png",
    "/favicon-16x16.png",
    "/favicon-32x32.png",
    "/favicon-96x96.png",
    "/favicon-192x192.png",
    "/favicon.ico",
    "/site.webmanifest",
    "/web-app-manifest-192x192.png",
    "/web-app-manifest-512x512.png",
    "/android-chrome-192x192.png",
    "/android-chrome-512x512.png",
]


class InactivityTimeoutException(Exception):
    """
    Custom exception to signal server inactivity timeout.
    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """

    pass


class MajorServerSideException(Exception):
    """
    Custom exception to signal extreme cli game fault.
    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """

    pass


class NoDataException(Exception):
    """
    Custom Exception to pass when no data is read from html file
    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """

    pass


class ThreadedHandler(http.server.BaseHTTPRequestHandler):
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

    # Handle GET requests for the root path and specific pages
    def do_GET(self) -> None:
        """
        Handles GET requests for the root path and specific pages.

        If the path is not recognized, sends a 404 error response.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        global password_pending, ending_server, player_session_store
        if self.path == "/":
            return self.redirect("/login")
        elif self.path == "/login":
            return self.serve_login()
        elif self.path == "/register":
            return self.serve_register()
        elif "static" in self.path:
            return self.serve_file()
        elif self.path in icons:
            return self.serve_icons()

        user_session_id = self.get_cookie("session_id")
        if not user_session_id or not user_session_id in player_session_store:
            return self.redirect("/login")
        player_session_store[session_id]["last_active"] = time.time()

        if self.path == "/stats":
            return self.serve_stats()
        elif self.path == "/game":
            return self.serve_game()
        elif self.path == "/home":
            return self.serve_home()
        else:
            self.send_error(404, "Page not found")

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

    def serve_login(self) -> None:
        try:
            # Send a successful response with HTML content
            self.serve_page(self.read_html(LOGIN_HTML))
        except Exception as e:
            # Send error response if the login page cannot be loaded
            self.send_error(201, f"Error loading login page: {e}")

    def serve_register(self) -> None:
        try:
            # Send a successful response with HTML content
            self.serve_page(self.read_html(REGISTER_HTML))
        except Exception as e:
            # Send error response if the login page cannot be loaded
            self.send_error(202, f"Error loading register page: {e}")

    def serve_stats(self) -> None:
        try:
            # Send a successful response with HTML content
            self.serve_page(self.read_html(STATS_HTML))
        except Exception as e:
            # Send error response if the login page cannot be loaded
            self.send_error(203, f"Error loading stats page: {e}")

    def serve_game(self) -> None:
        try:
            # Send a successful response with HTML content
            self.serve_page(self.read_html(GAME_HTML))
        except Exception as e:
            # Send error response if the login page cannot be loaded
            self.send_error(204, f"Error loading game page: {e}")

    def serve_home(self) -> None:
        try:
            # Send a successful response with HTML content
            self.serve_page(self.read_html(HOME_HTML))
        except Exception as e:
            # Send error response if the login page cannot be loaded
            self.send_error(205, f"Error loading home page: {e}")

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

    def handle_make_game(self) -> None:
        """
        Handles the creation of games and instances, auto adds instances and
        removes from list of non-binded ips

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """

        global promiscuis_ips
        if len(promiscuis_ips) < 2:
            return

        list1 = list(promiscuis_ips)
        player1 = random.choice(list1)
        player2 = random.choice(list1)

        promiscuis_ips.remove(player1)
        promiscuis_ips.remove(player2)

        instance_pointer = open_new_instance()
        active_games[hash(instance_pointer)] = {
            "player_ips": [player1, player2],
            "lua_instance": instance_pointer,
        }

    def do_POST(self) -> None:
        """
        Handles all POST requests to the server.

        This function determines the type of POST request and calls the appropriate
        handler function. The following POST requests are handled:

            - /login: Handles user login.
            - /register: Handles user registration.
            - /stats: Handles user stats retrieval.
            - /game: Handles game logic.
            - /Search: Handles matchmaking.
            - /Cancel: Handles cancelling matchmaking.
            - /Rematch: Handles rematching (currently not implemented).

        :return: None

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        global promiscuis_ips
        if self.path == "/login":
            self.handle_login()
        elif self.path == "/register":
            self.handle_register()
        elif self.path == "/stats":
            self.handle_stats()
        elif self.path == "/game":
            self.handle_game()
        elif self.path == "/Search":
            client = self.client_address[0]
            promiscuis_ips.add(client)
            # if ip is not in promiscuis_ips, add it? Also check connected ips, from new session store

            self.handle_make_game()
            # Need to send a package back saying starting matchmaking
        elif self.path == "/Cancel":
            # Need to add handler to cancel match making
            # Will send back package saying to cancel animation for mm
            if self.client_address[0] in promiscuis_ips:
                promiscuis_ips.remove(self.client_address[0])
        elif self.path == "/Rematch":
            # add code for rematching here
            raise NotImplementedError

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

        global error_found
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
            error_found = True
            exit(1)  # Exit on critical error

    def handle_login(self) -> None:
        """
        Handles the login of a user.

        Parameters
        ----------
        self : http.server.BaseHTTPRequestHandler
            The HTTP request handler instance.

        Returns
        -------
        None

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        global error_found
        data = self.read_post_request()

        session_id = secrets.token_hex(16)

        username = data["username"]
        password = data["password"]
        if not username:
            return None

        hashed, salt = get_username_and_pass(username)
        if not (hashed and salt):
            self.redirect("/register")
            return None
        if not check_password(password, hashed, salt):
            # Send header back stating user got username/ password wrong
            print("ERROR ERROR ERROR NOT HANDLED YET, user got password wrong!!")
            return None

        player_session_store[session_id] = {
            "username": username,
            "ip": self.client_address[0],
            "last_active": time.time(),
        }  # Store username - ip pair with session id

        self.send_response(200)
        self.send_header(
            "Set-Cookie", f"session_id={session_id}; HttpOnly; Secure; SameSite=Strict"
        )
        self.end_headers()
        print(f"User {username} logged in from {self.client_address[0]}")
        self.redirect("/home")


# This makes the new server instance
def open_new_instance() -> subprocess.Popen:
    """
    Launches a new game instance as a subprocess and returns the process object.

    This function attempts to start a new game instance using the global
    `game_cli` command. It creates a new session for the subprocess and captures
    both the standard output and standard error streams. If the subprocess
    returns a non-zero exit code or an error occurs, the function prints an
    error message and returns None. If the output contains the word "good",
    indicating successful execution, the process object is returned.

    Returns:
        subprocess.Popen: The process object if the instance starts successfully,
                          otherwise None.

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """

    global error_found, instance_count
    try:
        server_instance = subprocess.Popen(
            game_cli,
            shell=True,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Uses new session = true and pipes output and error
        if server_instance.poll() is not None:
            print("Error: Server instance is already closed.")
            raise MajorServerSideException("Game cli could not be initiated")

        # Read output
        ready, _, _ = select.select(
            [server_instance.stdout, server_instance.stderr], [], [], 1
        )

        out, error = "", ""

        if server_instance.stdout in ready:
            out = server_instance.stdout.readline().strip()
        if server_instance.stderr in ready:
            error = server_instance.stderr.readline().strip()

        if error != "":
            print(f"Error: {error}")
            program.terminate()
            return None

        if "good" in out:
            instance_count += 1
            return server_instance

        raise Exception("Did not receive expected response")
    except Exception as e:
        if server_instance:
            server_instance.terminate()
        print(f"An error occurred: {e}")
        error_found = True
        return None


def communicate(command: str, server_instance: subprocess.Popen = None) -> str:
    """
    Communicates with a server instance.

    This function communicates with a server instance using the given command.
    If no server instance is given, it will create a new one. If the command
    fails, it will print an error and exit. If the server instance fails,
    it will print an error and exit.

    Parameters:
        command (str): The command to send to the server instance.
        server_instance (subprocess.Popen): The server instance to communicate
            with. If not given, a new instance is created.

    Returns:
        str: The output of the command.

    Raises:
        MajorServerSideException: If the server instance could not be created.

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    global error_found
    try:
        if not server_instance:
            server_instance = open_new_instance()
            if not server_instance:
                raise MajorServerSideException("Instance could not be created")
    except Exception as e:
        error_found = True
        print(f"Major fault found: {e}")
        exit(1)

    try:
        # Uses new session = true and pipes output and error
        if server_instance.poll() is not None:
            try:
                server_instance.terminate()
            except:
                pass
            return "Collapse"

        # Send input via stdin.write() instead of communicate()
        server_instance.stdin.write(command + "\n")
        server_instance.stdin.flush()

        # Read output
        ready, _, _ = select.select(
            [server_instance.stdout, server_instance.stderr], [], [], 3
        )

        out, error = "", ""

        if server_instance.stdout in ready:
            out = server_instance.stdout.readline().strip()
        if server_instance.stderr in ready:
            error = server_instance.stderr.readline().strip()
        # Determine returncode
        if error != "":
            print(f"Error: {error.strip()}")
            return error
        return out
    except Exception as e:
        print(f"An error occurred: {e}: Instance: {server_instance}")
        server_instance.terminate()
        return "Collapse"


def instance_thread() -> None:
    global timeout, ending, error_found, thread_queue, instance_count
    try:
        instance = open_new_instance()
        if not instance:
            raise MajorServerSideException("Instance could not be created")
    except Exception as e:
        error_found = True
        print(f"Major fault found: {e}")
        exit(1)

    while not (error_found or ending_server or error_found):
        try:
            message = thread_queue.get(block=True, timeout=10)
            if message == "INSTANCE TERMINATE":
                print(message)
                instance_count -= 1
                return instance.send_signal(sig=signal.SIGTERM)
        except queue.Empty as e:
            out = communicate("Ping", instance)
            # Ensures the instance is up and running
            if out != "Pong":
                instance_count -= 1
                return instance.send_signal(sig=signal.SIGINT)
            print(out.strip())
            time.sleep(1)
        except Exception as e:
            print(f"Error found: {e}")
        else:
            # Send message to instance
            try:
                command = communicate(message, instance)
                if command == "Collapse":
                    try:
                        instance.send_signal(sig=signal.SIGTERM)
                    except:
                        pass
                    instance_count -= 1
                    print("An instance has collapsed!")
                    print(
                        "Killing current thread and reputting command back into queue."
                    )
                    return thread_queue.put(message, block=True)

                # Send back to callee
                output.append(message, command)
            except:
                try:
                    instance.send_signal(sig=signal.SIGKILL)
                except:
                    pass
                instance_count -= 1
                raise MajorServerSideException(
                    "An instance has gone stale! Aborted the child."
                )


def instance_thread_handler(
    time_check: int = 5, min_instance: int = 2, max_instance: int = sys.maxsize
) -> None:
    global instance_count, thread_queue, ending_server, timeout, error_found
    check_full = False
    check_empty = False
    while not (ending_server or timeout or error_found):
        if thread_queue.qsize() > 10:
            check_empty = False
            if check_full and instance_count < max_instance:
                threading.Thread(target=instance_thread).start()
            else:
                check_full = True
        elif thread_queue.qsize() < 5:
            check_full = False
            if check_empty and instance_count > min_instance:
                thread_queue.put("INSTANCE TERMINATE", block=True, timeout=5)
            else:
                check_empty = True
        else:
            check_empty = False

        if instance_count < min_instance:
            threading.Thread(target=instance_thread).start()
        time.sleep(time_check)


class TimeoutThreadingHTTPServer(http.server.ThreadingHTTPServer):
    last_activity_time = time.time()
    inactivity_timeout = 60 * 10

    def __init__(self, server_address: tuple, RequestHandlerClass) -> None:
        super().__init__(server_address, RequestHandlerClass)

    def server_activate(self) -> None:
        """
        Starts the server and spawns a separate thread to monitor inactivity.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        super().server_activate()
        threading.Thread(target=self.monitor_inactivity).start()
        self.last_activity_time = time.time()

    def process_request(self, request, client_address) -> None:
        """
        Processes an incoming request and updates the last activity timestamp.

        This method is called to handle each incoming request to the server. It
        updates the `last_activity_time` to the current time to indicate that there
        has been recent activity, and then delegates the actual processing of the
        request to the parent class's `process_request` method.

        Parameters:
            request: The incoming request to be processed.
            client_address: The address of the client making the request.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """

        self.last_activity_time = time.time()
        super().process_request(request, client_address)

    def monitor_inactivity(self) -> None:
        """
        Monitors server inactivity and shuts it down if it has been idle for too long.

        This method runs in its own thread and continuously checks if the server
        has been idle for longer than the specified inactivity timeout. If it has,
        it prints a message, sets the timeout flag and shuts down the server.

        The inactivity timeout is in seconds and defaults to 5 minutes.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        global timeout
        while not (ending_server or error_found):
            # Check if the server has been idle for too long
            if time.time() - self.last_activity_time > self.inactivity_timeout:
                print("No activity for 5 minutes, shutting down the server.")
                timeout = True
                break
            time.sleep(15)  # Check every 15 seconds
        self.shutdown()


# Set up and run the HTTP server
def run(server_class=TimeoutThreadingHTTPServer, handler_class=ThreadedHandler) -> None:
    """
    Starts and runs the HTTP server.

    This function sets up and runs the HTTP server with the given server and
    handler classes. It listens on localhost:5000 and logs a message to indicate
    when the server is started. When the server is terminated, either by a
    KeyboardInterrupt or an exception, it logs a message and terminates the
    process. Finally, it closes the server and sets the ending flag to True.

    Parameters:
        server_class (class): The class of the HTTP server. Defaults to
            TimeoutThreadingHTTPServer.
        handler_class (class): The class of the request handler. Defaults to
            ThreadedHandler.

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    global httpd, ending
    server_address = ("", 5000)  # Server listens on localhost:5000
    httpd = server_class(server_address, handler_class)
    print("Starting server on port 5000...")
    try:
        # Create the http timeout handler
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("User Terminated webserver")
        exit(0)
    except Exception as e:
        print("WebServer Terminated with error: ", e)
        exit(1)

    ending = True
    httpd.server_close()


def kill_active_threads(active: threading.Thread) -> None:
    """
    Terminates all active threads except for the main thread and the active thread

    This function is used to terminate all active threads except for the main thread
    and the active thread. It waits for each thread to terminate for up to 10 seconds,
    and if the thread is still alive after that, it terminates the thread with
    SIGTERM.

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    try:
        main = threading.main_thread()
        for thread in threading.enumerate():
            if thread == active or thread == main:
                continue
            if thread.daemon:
                print(f"Thread is daemonized, skipping: {thread.name}")
                continue

            print(f"Waiting for thread: {thread.name}")
            thread.join(15)

            if thread.is_alive():
                print(f"Killing thread with main after termination: {thread.name}")
    except KeyboardInterrupt as e:
        print(e)
        os.kill(os.getpid(), signal.SIGTERM)
    except Exception as e:
        print("wtf happened here (Encoutered new error in kill_active_threads) ", e)


def db_loop() -> None:
    """
    Handles database operations synchronously in a separate thread from main or callee.

    This function enters an infinite loop until one of the following conditions
    is met: the server has been idle for too long, a major fault has been
    detected, or the server has been signaled to terminate.

    In each iteration, it checks for and executes any database commands that
    have been queued in the `db_command_hook` queue. Database commands are
    represented as tuples of the form `(action, params)`, where `action` is a
    string indicating the type of database operation to perform and `params` is
    a list of parameters to pass to the operation function.

    Currently, the supported operations are `INSERT` and `UPDATE`, which
    correspond to the `create_new_user` and `change_user_data` functions
    respectively.

    After executing all queued commands, the function waits for 3 seconds before
    checking again.

    When the loop exits, the function terminates the process with exit code 0.
    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    while not (timeout or error_found or ending_server):
        while not db_command_hook.empty():
            action, params = db_command_hook.get()
            if action == "INSERT":
                create_new_user(*params)
            elif action == "UPDATE":
                change_user_data(action, params)
        time.sleep(5)
    db_command_hook.shutdown()


def update_elo(
    player_rating: float, opponent_rating: float, score: float, K: int = 32
) -> float:
    """
    Update a player's Elo rating after a game.

    Args:
    player_rating (float): The current player's rating.
    opponent_rating (float): The opponent's rating.
    score (float): The score of the player (1 for win, 0.5 for draw, 0 for loss).
    K (int): The K-factor, typically 32.

    Returns:
    float: The updated player rating.

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    expected_score = calculate_expected_score(player_rating, opponent_rating)
    new_rating = player_rating + K * (score - expected_score)
    return new_rating


def calculate_expected_score(player_rating: float, opponent_rating: float) -> float:
    """
    Calculate the expected score based on the Elo rating system.
    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    return 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))


def change_user_data(action: str, info: dict) -> None:
    """
    Update an existing user's data in the database.
    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    global db_connection, db_cursor, error_found

    if not (db_connection and db_cursor):  # Ensure DB is initialized
        error_found = True
        print("Error: Database not initialized")
        exit(1)

    try:
        command = "UPDATE users SET "
        data_list = []

        # Extract column names from the action string
        fields = action.split()[1:]  # Remove "UPDATE"

        if not fields:
            return print("Error: No fields specified for update.")

        for field in fields:
            if field in info:
                command += f"{field} = ?, "
                data_list.append(info[field])

        # Remove trailing comma and space, add WHERE condition
        command = command.rstrip(", ") + " WHERE username = ?"
        data_list.append(info["old_name"])  # Add WHERE value

        # Execute the update query
        db_cursor.execute(command, data_list)
        db_connection.commit()

        print(f"User {info['old_name']} updated successfully!")
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")


def get_username_and_pass(name: str) -> dict:
    global db_connection, db_cursor, error_found
    if not (db_connection and db_cursor):
        error_found = True
        print("DB not initialized")
        exit(1)

    try:
        db_cursor.execute("SELECT * FROM users WHERE username = ?", (name))
        user_data = db_cursor.fetchone()
        return {
            "username": user_data[1],
            "password_hash": user_data[2],
            "salt": user_data[3],
        }
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")
        return {}


def create_new_user(name: str, password: str) -> None:
    """
    Insert a new user into the database.
    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    global db_connection, db_cursor, error_found
    if not (db_connection and db_cursor):
        error_found = True
        print("DB not initialized")
        exit(1)

    try:
        password_hash, salt = generate_password_hash(password)
        db_cursor.execute(
            """
            INSERT INTO users (username, password_hash, salt, elo, games, wins, join_date, last_game)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, password_hash, salt, 500, 0, datetime.datetime.now(), None),
        )
        db_connection.commit()
        print(f"User {name} added successfully!")
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")


def create_db(db_name: str = "game.db") -> None:
    """
    Connects to a given SQLite database and creates the necessary table if it doesn't exist.

    Args:
        db_name (str): The name of the SQLite database file to connect to. Defaults to 'game.db'.

    Raises:
        Exception: If connecting to the database or creating the table fails.

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    global db_connection, db_cursor, error_found
    try:
        # Ensures the db file is made alongside the .py file
        os.chdir(os.path.dirname(__file__))
        db_connection = sqlite3.connect(db_name)
        db_cursor = db_connection.cursor()
        db_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                elo INTEGER NOT NULL DEFAULT 500,
                wins INTEGER NOT NULL DEFAULT 0,
                draws INTEGER NOT NULL DEFAULT 0,
                join_date TEXT NOT NULL,
                last_game TEXT
            )
            """
        )
        db_connection.commit()
        # Switches back to the frontend directory
        os.chdir("../frontend")
    except Exception as e:
        error_found = True
        print(f"Error found: {e}")
        exit(1)


def generate_password_hash(password: str, salt: bytes = None) -> tuple:
    """
    Generates a SHA512 hash of the given password and an optional salt.

    If no salt is provided, a random 16-byte salt is generated.

    Returns a tuple containing the hashed password and the salt as hexadecimal strings.

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    if not salt:
        salt = os.urandom(16)
    hash_obj = hashlib.sha512(salt + password.encode())
    hashed_password = hash_obj.hexdigest()

    return hashed_password, salt.hex()


def decypher_password(password: str, hashed_password: str, salt: bytes) -> bool:
    # Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    return generate_password_hash(password, bytes.fromhex(salt))[0] == hashed_password


def check_inactive_sessions() -> None:
    """
    Periodically checks the stored sessions for inactivity.

    If a session has been inactive for more than 600 seconds, it is removed from the session store.

    This function runs in an infinite loop until the server is stopped or an error is found.

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    while not (ending_server or timeout or error_found):
        for session_id in player_session_store:
            if time.time() - player_session_store[session_id]["last_active"] > 600:
                del player_session_store[session_id]
        time.sleep(10)


def check_inactivity() -> None:
    """
    Monitors server inactivity and handles shutdown procedures.

    This function runs continuously, checking for server inactivity,
    errors, or termination signals. If an inactivity timeout or error is
    detected, it closes the server connection and raises the appropriate
    exception. If a termination signal is detected, the function breaks
    the loop and proceeds to shutdown procedures.

    After exiting the loop, it ensures that all active threads are
    terminated and the database connection is closed. Finally, it
    terminates the process.

    Exceptions:
        InactivityTimeoutException: Raised when the server exceeds the
                                    inactivity timeout.
        Exception: Raised for any general error that requires the server
                   to stop.

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """

    global httpd, timeout, error_found, ending_server, db_connection
    try:
        while True:
            time.sleep(5)
            if timeout:
                raise InactivityTimeoutException(
                    "Inactivity limit reached, stopping server"
                )
            if error_found:
                raise Exception("Error found, stopping server")
            if ending_server:
                break
    except KeyboardInterrupt:
        print("Server stopping")
        ending_server = True
        pass
    except Exception as e:
        print(f"{e}")
        error_found = True

    httpd.shutdown()
    httpd.server_close()
    kill_active_threads(threading.current_thread())
    if db_connection:
        db_connection.close()
    os.kill(os.getpid(), signal.SIGTERM)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR! Pass a call to indicate the game server")
        exit(1)

    os.chdir(os.path.dirname(__file__))
    os.chdir("../chess_backend")
    game_cli = "lua " + os.path.abspath("cli.lua") + " -c"
    print(game_cli)

    if len(sys.argv) > 2:
        create_db(sys.argv[2])
    else:
        create_db(sys.argv[1] + ".db")

    if len(sys.argv) > 3:
        bot_cli = sys.argv[3]

    threading.Thread(target=run, daemon=True).start()
    threading.Thread(target=instance_thread_handler).start()
    threading.Thread(target=db_loop).start()
    threading.Thread(target=check_inactive_sessions).start()

    check_inactivity()
