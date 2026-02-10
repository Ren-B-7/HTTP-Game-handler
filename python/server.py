"""
Chess server implementation with WebSocket support, session management, Engine
management, input sanitization, and database operations.

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

# Thread/ program
import signal
import sys
import threading
import traceback
import time
from typing import Optional, Tuple

import ssl

# Game
import json
import queue

# Config
from utils.EngineHandler import EnginePool, InstanceInoperable
from utils.SanitizeOrValidate import (
    sanitize_filename,
    valid_input,
    valid_username,
    is_valid_length,
    valid_utf8,
)

# Import constants and exceptions
from utils.constants import (
    config,
    SCRIPT_DIR,
    FRONTEND_DIR,
    SERVER_HOST,
    SERVER_PORT,
    SERVER_TIMEOUT,
    GAME_HANDLER,
    ACTIVE_DB,
    SESSION_DB,
    SERVER_STATE,
    SESSION_MANAGER,
    COMPRESSION_CACHE,
    ACTIVE_GAMES,
    MATCHMAKING_QUEUE,
    DB_CONNECTION,
    HTTPD,
    ENGINE_POOL,
    LOGIN_HTML,
    REGISTER_HTML,
    GAME_HTML,
    STATS_HTML,
    HOME_HTML,
    PROFILE_HTML,
    ICONS_DIRECTORY,
    ICON_FILES,
    CERT_FILE,
    KEY_FILE,
)

from utils.exceptions import (
    DBException,
    MajorServerSideException,
    ProcessingError,
    NoDataException,
)

from ThreadedHttpServer import TimeoutThreadingHTTPServer, SSLTimeoutThreadingServer
from HttpSocketHandler import ThreadedHandlerWithSockets

from auth import *
from game import *
from database import *


class GameHandler(ThreadedHandlerWithSockets):
    """HTTP/WebSocket handler with authentication and game logic."""

    def check_auth(self) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
        """
        Check if user is authenticated.

        Returns:
            tuple: (is_authenticated, session_id, username, user_id)
        """
        session_id = self.get_cookie("session_id")

        if not session_id:
            return False, None, None, None

        # Validate session_id format
        if not valid_input(session_id) or not is_valid_length(session_id, 1, 128):
            return False, None, None, None

        session = SESSION_MANAGER.get_session(session_id)
        if not session:
            return False, None, None, None

        # Update activity
        SESSION_MANAGER.update_activity(session_id)

        return True, session_id, session["username"], session["user_id"]

    def do_GET(self) -> None:
        """Handle GET requests and WebSocket upgrades."""
        # Handle WebSocket upgrade early
        if self.headers.get("Upgrade", "").lower() == "websocket":
            return self._handle_websocket()

        # Sanitize filenames to block directory traversal attacks
        sanitize_filename(self.path)

        # Deliver non-static/ static directory files first
        if "static/" in self.path:
            return self.serve_file(
                file=(FRONTEND_DIR / self.path.lstrip("/")).resolve(),
                cache=not ("non-static" in self.path),
                compress=True,
            )

        # If no path is given default to login
        if self.path == "/":
            return self.redirect("/login")
        if self.path == "/login":
            return self.serve_page(page=LOGIN_HTML)
        if self.path == "/register":
            return self.serve_page(page=REGISTER_HTML)
        if (self.path in ICON_FILES) or ("icons" in self.path):
            return self.serve_icons(ICONS_DIRECTORY)

        # Auth check for protected routes
        is_auth, _, _, user_id = self.check_auth()
        if not is_auth:
            return self.redirect("/login")
        # Authenticated routes
        if self.path == "/stats":
            self.serve_page(page=STATS_HTML)
        elif self.path == "/game":
            # Check if the player is in an active game, if no we redirect to the
            # home page
            for _, game_data in ACTIVE_GAMES.items():
                if user_id in [
                    game_data["player1"]["user_id"],
                    game_data["player2"]["user_id"],
                ]:
                    return self.serve_page(page=GAME_HTML)
            return self.serve_page(page=HOME_HTML)
        elif self.path == "/home":
            self.serve_page(page=HOME_HTML)
        elif self.path == "/profile":
            self.serve_page(page=PROFILE_HTML)
        else:
            self.send_error(404, "NotFound", f"Page not found: {self.path}")

    def do_POST(self) -> None:
        """Handle all POST requests to the server."""
        if self.path == "/login":
            self.handle_login()
        elif self.path == "/register":
            self.handle_register()
        elif self.path == "/session":
            self.handle_session()
        elif self.path == "/home/search":
            self.handle_search()
        elif self.path == "/home/cancel":
            self.handle_cancel_search()
        elif self.path == "/stats":
            self.handle_stats()
        elif self.path == "/profile/update-username":
            self.handle_change_username()
        elif self.path == "/profile/update-password":
            self.handle_change_password()
        elif self.path == "/profile/delete-account":
            self.handle_delete_account()
        elif self.path == "/logout":
            self.handle_logout()
        else:
            self.send_error(404, "NotFound", f"Handler not found: {self.path}")

    def handle_login(self) -> None:
        """Handle user login with comprehensive validation."""
        try:
            data = self.read_post_request()
            if not data:
                raise NoDataException("No data to be read")

            username = data.get("username", "")
            password = data.get("password", "")

            # Input validation
            if not username or not password:
                raise ProcessingError("Missing credentials", 400)

            # Validate username format
            if not valid_username(username):
                raise ProcessingError("Invalid username format", 400)

            # Validate username length
            if not is_valid_length(username, 1, 128):
                raise ProcessingError(
                    "Username must be between 1 and 128 characters", 400
                )

            # Validate password
            if not valid_input(password):
                raise ProcessingError("Invalid password format", 400)

            if not is_valid_length(password, 1, 128):
                raise ProcessingError("Password length invalid", 400)

            # Get user data from database
            user_data = get_username_and_pass(username)

            if not user_data:
                raise ProcessingError("Invalid username or password", 401)

            # Verify password
            if not compare_password(
                password, user_data["password_hash"], user_data["salt"]
            ):
                raise ProcessingError("Invalid username or password", 401)

            self.session_login(user_id=user_data["user_id"], username=username)
        except ProcessingError as e:
            self.json_error(e.message, e.code)
        except NoDataException as e:
            self.json_error(f"No data to be read from request: {e}", 500)
        except Exception as e:
            self.json_error(f"Server error: {e}", 500)

    def handle_register(self) -> None:
        """Handle user registration with comprehensive validation."""
        try:
            data = self.read_post_request()
            if not data:
                raise ProcessingError("No data received", 400)

            username = data.get("username", "")
            password = data.get("password", "")
            confirm_password = data.get("confirm_password", "")

            # Validation
            if not (username and password and confirm_password):
                raise ProcessingError("Missing required fields", 400)

            if password != confirm_password:
                raise ProcessingError("Passwords do not match", 400)

            if not valid_username(username):
                raise ProcessingError("Username contains invalid characters", 400)

            if not is_valid_length(username, 3, 20):
                raise ProcessingError(
                    "Username must be between 3 and 20 characters", 400
                )

            if not is_valid_length(password, 12, 128):
                raise ProcessingError("Password must be at least 12 characters", 400)

            if not valid_input(password):
                raise ProcessingError("Password contains invalid characters", 400)

            # Create user
            user_id = create_new_user(username, password)
            if not user_id:
                raise ProcessingError("Could not create new username", 500)
            self.session_login(user_id=user_id, username=username)
        except ProcessingError as e:
            self.json_error(e.message, e.code)
        except Exception as e:
            self.json_error(f"Registration error: {e}", 500)

    def handle_session(self) -> None:
        """Handle session validation and return current user info."""
        try:
            is_auth, session_id, username, user_id = self.check_auth()

            if not is_auth:
                raise ProcessingError("Not authenticated", 401)
            if not (session_id and username and user_id):
                raise ProcessingError("Could not retrieve user info", 500)

            stats = get_user_stats_by_id(user_id)
            if not stats:
                raise ProcessingError("Stats not found", 404)

            payload = {
                "username": username,
                "elo": stats["elo"],
            }

            self.json_success(data=payload)
        except ProcessingError as e:
            self.json_error(e.message, e.code)
        except Exception as e:
            self.json_error(f"Session error: {e}", 500)

    def handle_logout(self) -> None:
        """Handle user logout."""
        session_id = self.get_cookie("session_id")
        if session_id and valid_input(session_id):
            SESSION_MANAGER.delete_session(session_id)
        self.json_success(message="Logged out successfully")

    def handle_change_username(self) -> None:
        """Handle username change request with validation."""
        try:
            is_auth, session_id, username, user_id = self.check_auth()

            if not is_auth:
                raise ProcessingError("Not authenticated", 401)
            if not (session_id and username and user_id):
                raise ProcessingError("Could not retrieve user info", 500)

            data = self.read_post_request()
            if not data:
                raise NoDataException("No data to be read")

            new_username = data.get("new_username", "")
            password = data.get("password", "")

            # Validation
            if not new_username or not password:
                raise ProcessingError("Missing credentials", 400)

            if not valid_username(new_username):
                raise ProcessingError("Username contains invalid characters", 400)

            if not is_valid_length(new_username, 3, 20):
                raise ProcessingError(
                    "Username must be between 3 and 20 characters", 400
                )

            if not valid_input(password):
                raise ProcessingError("Invalid password", 400)

            # Verify existing credentials
            user_data = get_username_and_pass(username)
            if not user_data:
                raise ProcessingError("Invalid username or password", 401)
            if not compare_password(
                password, user_data["password_hash"], user_data["salt"]
            ):
                raise ProcessingError("Invalid username or password", 401)

            # Update username
            if not update_username(user_id, new_username):
                raise ProcessingError("Username already exists", 409)

            SESSION_MANAGER.update_username_in_sessions(user_id, new_username)
            SESSION_MANAGER.update_activity(session_id)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            response = json.dumps(
                {"success": True, "message": "Username updated successfully"}
            )
            self.wfile.write(response.encode("utf-8"))

        except ProcessingError as e:
            self.json_error(e.message, e.code)
        except Exception as e:
            self.json_error(f"Error updating username: {e}", 500)

    def handle_change_password(self) -> None:
        """Handle password change request with validation."""
        try:
            is_auth, session_id, username, user_id = self.check_auth()
            if not is_auth:
                raise ProcessingError("Not authenticated", 401)
            if not (session_id and username and user_id):
                raise ProcessingError("Could not retrieve user info", 500)

            data = self.read_post_request()
            if not data:
                raise ProcessingError("No data received", 400)

            current_password = data.get("current_password", "")
            new_password = data.get("new_password", "")
            confirm_password = data.get("confirm_password", "")

            # Validation
            if not (current_password and new_password):
                raise ProcessingError("Current and new passwords are required", 400)

            if new_password != confirm_password:
                raise ProcessingError("Passwords don't match", 400)

            if not is_valid_length(new_password, 12, 128):
                raise ProcessingError(
                    "New password must be at least 12 characters", 400
                )

            if not valid_input(new_password):
                raise ProcessingError("Password contains invalid characters", 400)

            user_data = get_username_and_pass(username)
            if not user_data:
                raise ProcessingError("User not found", 404)
            if not compare_password(
                current_password, user_data["password_hash"], user_data["salt"]
            ):
                raise ProcessingError("Current password is incorrect", 401)

            # Update password and invalidate other sessions
            if not update_password(user_id, new_password):
                raise ProcessingError("Failed to update password", 500)

            for sid in SESSION_MANAGER.get_user_sessions(user_id):
                if sid != session_id:
                    SESSION_MANAGER.delete_session(sid)

            SESSION_MANAGER.update_activity(session_id)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            response = json.dumps(
                {"success": True, "message": "Password updated successfully"}
            )
            self.wfile.write(response.encode("utf-8"))

        except ProcessingError as e:
            self.json_error(e.message, e.code)
        except Exception as e:
            self.json_error(f"Error updating password: {e}", 500)

    def handle_delete_account(self) -> None:
        """Handle account deletion request."""
        try:
            # Check authentication
            is_auth, session_id, username, user_id = self.check_auth()
            if not is_auth:
                raise ProcessingError("Not authenticated", 401)
            if not (session_id and username and user_id):
                raise ProcessingError("Could not retrieve user info", 500)

            # Read request data
            data = self.read_post_request()
            if not data:
                raise ProcessingError("No data received", 400)

            password = data.get("password", "")

            # Validate password
            if not password:
                raise ProcessingError("Password is required for confirmation", 400)

            if not valid_input(password):
                raise ProcessingError("Invalid password", 400)

            # Verify password
            user_data = get_username_and_pass(username)
            if not user_data:
                raise ProcessingError("User not found", 404)

            if not compare_password(
                password, user_data["password_hash"], user_data["salt"]
            ):
                raise ProcessingError("Invalid password", 401)

            # Delete user account
            if delete_user_account(user_id):
                # Logout all sessions (using user_id)
                SESSION_MANAGER.logout_all_user_sessions(user_id)

                self.json_success(message="Account deleted successfully")
            else:
                raise ProcessingError("Failed to delete account", 500)
        except ProcessingError as e:
            self.json_error(e.message, e.code)
        except Exception as e:
            self.json_error(f"Error deleting account: {e}", 500)

    def handle_search(self) -> None:
        """Handle matchmaking search request."""
        global MATCHMAKING_QUEUE, MATCHMAKING_RESULTS

        try:
            is_auth, session_id, username, user_id = self.check_auth()

            if not is_auth:
                raise ProcessingError("Not authenticated", 401)
            if not (session_id and username and user_id):
                raise ProcessingError("Could not retrieve user info", 500)

            # Check if player already has an active game
            for _, game_data in ACTIVE_GAMES.items():
                if user_id in [
                    game_data["player1"]["user_id"],
                    game_data["player2"]["user_id"],
                ]:
                    raise ProcessingError("Already in an active game", 409)

            # Add to matchmaking queue
            MATCHMAKING_QUEUE.put(
                {
                    "user_id": user_id,
                    "username": username,
                    "session_id": session_id,
                }
            )

            self.json_success(message="Searching for opponent...")

        except ProcessingError as e:
            self.json_error(e.message, e.code)
        except Exception as e:
            self.json_error(f"Search error: {e}", 500)

    def handle_cancel_search(self) -> None:
        """Handle matchmaking cancellation request."""
        global MATCHMAKING_QUEUE

        try:
            is_auth, session_id, _, _ = self.check_auth()

            if not is_auth:
                raise ProcessingError("Not authenticated", 401)

            # Remove from queue (rebuild queue without this player)
            temp_queue = queue.Queue()
            removed = False

            while not MATCHMAKING_QUEUE.empty():
                try:
                    player = MATCHMAKING_QUEUE.get_nowait()
                    if player.get("session_id") != session_id:
                        temp_queue.put(player)
                    else:
                        removed = True
                except queue.Empty:
                    break

            # Restore queue
            while not temp_queue.empty():
                MATCHMAKING_QUEUE.put(temp_queue.get())

            if removed:
                self.json_success(message="Search cancelled")
            else:
                raise ProcessingError("Not currently searching", 404)

        except ProcessingError as e:
            self.json_error(e.message, e.code)
        except Exception as e:
            self.json_error(f"Cancel error: {e}", 500)

    def handle_stats(self) -> None:
        """Handle stats retrieval request."""
        try:
            is_auth, _, _, user_id = self.check_auth()
            if not (is_auth and user_id):
                raise ProcessingError("Not authenticated", 401)

            stats = get_user_stats_by_id(user_id)
            if stats:
                self.json_success(data=stats)
            else:
                raise ProcessingError("Stats not found", 404)
        except ProcessingError as e:
            self.json_error(e.message, e.code)
        except KeyError as e:
            self.json_error("Data read incorrectly from dictionary/ database", 500)
            raise KeyError("Data read incorrectly from dictionary") from e

    # WebSocket Handlers
    def on_ws_connected(self):
        """Called when WebSocket connection is established."""
        global ACTIVE_GAMES

        try:
            # Get session from cookie
            session_id = self.get_cookie("session_id")
            if not session_id:
                self.send_message(
                    json.dumps({"type": "error", "message": "Not authenticated"})
                )
                self._ws_close()
                return

            # Validate session_id format
            if not valid_input(session_id) or not is_valid_length(session_id, 1, 128):
                self.send_message(
                    json.dumps({"type": "error", "message": "Invalid session"})
                )
                self._ws_close()
                return

            # Validate session
            session = SESSION_MANAGER.get_session(session_id)
            if not session:
                self.send_message(
                    json.dumps({"type": "error", "message": "Invalid session"})
                )
                self._ws_close()
                return

            username = session["username"]
            user_id = session["user_id"]

            # Store user info for later use
            self.user_id = user_id
            self.username = username
            self.session_id = session_id

            # Find the game this player is in
            player_game_id = None
            for game_id, game_data in ACTIVE_GAMES.items():
                if session_id in [
                    game_data["player1"]["session_id"],
                    game_data["player2"]["session_id"],
                ]:
                    player_game_id = game_id
                    break

            if not player_game_id:
                self.send_message(
                    json.dumps(
                        {
                            "type": "error",
                            "message": "No active game found. Please start matchmaking.",
                        }
                    )
                )
                self._ws_close()
                return

            # Store WebSocket connection and game_id
            self.game_id = player_game_id
            game = ACTIVE_GAMES[player_game_id]

            # Register WebSocket to correct player
            if game["player1"]["session_id"] == session_id:
                game["player1"]["websocket"] = self
                your_color = game["player1"]["color"]
                opponent_username = game["player2"]["username"]
            else:
                game["player2"]["websocket"] = self
                your_color = game["player2"]["color"]
                opponent_username = game["player1"]["username"]

            # Send game start message (matches client expectations)
            self.send_message(
                json.dumps(
                    {
                        "type": "game_start",
                        "game_id": player_game_id,
                        "your_color": your_color,
                        "your_username": username,
                        "opponent_username": opponent_username,
                        "fen": game["fen"],
                        "legal_moves": game["legal_moves"],
                        "current_turn": game["current_turn"],
                    }
                )
            )

            print(f"WebSocket connected for {username} in game {player_game_id}")

        except Exception as e:
            print(f"WebSocket connection error: {e}")
            traceback.print_exc()
            self.send_message(
                json.dumps({"type": "error", "message": "Connection error"})
            )
            self._ws_close()

    def on_ws_message(self, message):
        """Called when a message is received via WebSocket with validation."""
        global ACTIVE_GAMES

        try:
            # Validate message format and length
            if not message or not isinstance(message, str):
                self.send_message(
                    json.dumps({"type": "error", "message": "Invalid message format"})
                )
                return

            # Limit message size to prevent DoS
            if not is_valid_length(message, 1, 10000):
                self.send_message(
                    json.dumps({"type": "error", "message": "Message too large"})
                )
                return

            # Validate UTF-8
            if not valid_utf8(message):
                self.send_message(
                    json.dumps({"type": "error", "message": "Invalid message encoding"})
                )
                return

            data = json.loads(message)
            msg_type = data.get("type")

            # Validate message type
            if not msg_type or not isinstance(msg_type, str):
                self.send_message(
                    json.dumps({"type": "error", "message": "Missing message type"})
                )
                return

            # Get and validate session
            session_id = self.get_cookie("session_id")
            if not session_id:
                self.send_message(
                    json.dumps({"type": "error", "message": "Not authenticated"})
                )
                return

            if not valid_input(session_id):
                self.send_message(
                    json.dumps({"type": "error", "message": "Invalid session"})
                )
                return

            session = SESSION_MANAGER.get_session(session_id)
            if not session:
                self.send_message(
                    json.dumps({"type": "error", "message": "Invalid session"})
                )
                return

            username = session["username"]

            if not self.game_id or self.game_id not in ACTIVE_GAMES:
                self.send_message(
                    json.dumps({"type": "error", "message": "No active game"})
                )
                return

            game = ACTIVE_GAMES[self.game_id]

            # Handle different message types
            if msg_type == "handshake":
                # Client handshake - acknowledge
                self.send_message(
                    json.dumps({"type": "handshake_ack", "message": "Server ready"})
                )

            elif msg_type == "move":
                move_str = data.get("move")

                # Validate move string
                if not move_str or not isinstance(move_str, str):
                    self.send_message(
                        json.dumps({"type": "error", "message": "Invalid move format"})
                    )
                    return

                # Chess moves should be short (e.g., "e2e4", max ~10 chars)
                if not is_valid_length(move_str, 1, 20):
                    self.send_message(
                        json.dumps({"type": "error", "message": "Invalid move format"})
                    )
                    return

                # Validate move contains only safe characters
                if not valid_input(move_str):
                    self.send_message(
                        json.dumps({"type": "error", "message": "Invalid move format"})
                    )
                    return

                self.handle_ws_move(game, username, session_id, move_str)
            elif msg_type == "resign":
                self.handle_ws_resign(game, session_id)
            elif msg_type == "offer_draw":
                self.handle_ws_draw_offer(game, username, session_id)
            elif msg_type == "accept_draw":
                self.handle_ws_draw_accept(game)
            elif msg_type == "decline_draw":
                self.handle_ws_draw_decline(game, session_id)
            elif msg_type == "cancel_draw_offer":
                self.handle_ws_draw_cancel(game, session_id)
            elif msg_type == "pong":
                # Keep-alive response
                pass
            else:
                print(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            self.send_message(
                json.dumps({"type": "error", "message": "Invalid message format"})
            )
        except Exception as e:
            print(f"WebSocket message error: {e}")
            traceback.print_exc()
            self.send_message(
                json.dumps({"type": "error", "message": "Message processing error"})
            )

    def handle_ws_move(self, game, _username, session_id, move):
        """Process a move from WebSocket."""
        if not ENGINE_POOL:
            raise MajorServerSideException("Engine pool not initiated")
        try:
            # Verify it's player's turn
            player_color = (
                game["player1"]["color"]
                if game["player1"]["session_id"] == session_id
                else game["player2"]["color"]
            )

            if game["current_turn"] != player_color:
                self.send_message(
                    json.dumps({"type": "error", "message": "Not your turn"})
                )
                return

            if not move:
                self.send_message(
                    json.dumps({"type": "error", "message": "Invalid move format"})
                )
                return

            # Send to chess engine
            engine_request = {"reason": "move", "fen": game["fen"], "moves": move}

            if self.game_id:
                response = ENGINE_POOL.submit_task(self.game_id, engine_request)
            else:
                raise MajorServerSideException("Could not read game id")

            if not response:
                raise InstanceInoperable("Could not read from engine pool")

            if response.get("message") == "valid":
                # Extract legal moves from response
                new_legal_moves = response.get("possible_moves", [])

                # Update game state
                game["fen"] = response["fen"]
                game["moves"].append(move)
                game["legal_moves"] = new_legal_moves
                game["current_turn"] = (
                    "black" if game["current_turn"] == "white" else "white"
                )
                game["last_move_at"] = time.time()

                # Check for game end
                winner = response.get("winner")
                if winner:
                    # Game ended (checkmate, stalemate, etc.)
                    self.handle_game_end(
                        game, response.get("reason", "checkmate"), winner
                    )
                    return

                # Broadcast to both players
                state_message = json.dumps(
                    {
                        "type": "move_update",
                        "fen": game["fen"],
                        "next_turn": game["current_turn"],
                        "legal_moves": game["legal_moves"],
                        "last_move": move,
                        "move_history": game["moves"],
                    }
                )

                if game["player1"]["websocket"]:
                    game["player1"]["websocket"].send_message(state_message)
                if game["player2"]["websocket"]:
                    game["player2"]["websocket"].send_message(state_message)
            else:
                self.send_message(
                    json.dumps(
                        {
                            "type": "error",
                            "message": response.get("error", "Invalid move"),
                        }
                    )
                )

        except Exception as e:
            print(f"Move handling error: {e}")
            traceback.print_exc()
            self.send_message(
                json.dumps({"type": "error", "message": "Move processing error"})
            )

    def handle_ws_resign(self, game, session_id):
        """Handle resignation."""
        try:
            player_color = (
                game["player1"]["color"]
                if game["player1"]["session_id"] == session_id
                else game["player2"]["color"]
            )
            winner_color = "black" if player_color == "white" else "white"
            self.handle_game_end(game, "resignation", winner_color)
        except Exception as e:
            print(f"Resignation error: {e}")

    def handle_ws_draw_offer(self, game, username, session_id):
        """Handle draw offer."""
        try:
            # Notify opponent of draw offer
            opponent = (
                game["player2"]
                if game["player1"]["session_id"] == session_id
                else game["player1"]
            )
            if opponent["websocket"]:
                opponent["websocket"].send_message(
                    json.dumps(
                        {"type": "draw_offered", "message": f"{username} offers a draw"}
                    )
                )
        except Exception as e:
            print(f"Draw offer error: {e}")

    def handle_ws_draw_accept(self, game):
        """Handle draw acceptance."""
        try:
            # End game as draw
            self.handle_game_end(game, "draw", None)

            # Notify both players
            msg = json.dumps({"type": "draw_accepted", "message": "Draw accepted"})

            if game["player1"]["websocket"]:
                game["player1"]["websocket"].send_message(msg)
            if game["player2"]["websocket"]:
                game["player2"]["websocket"].send_message(msg)

        except Exception as e:
            print(f"Draw accept error: {e}")

    def handle_ws_draw_decline(self, game, session_id):
        """Handle draw decline."""
        try:
            # Notify the player who offered the draw
            opponent = (
                game["player2"]
                if game["player1"]["session_id"] == session_id
                else game["player1"]
            )

            if opponent["websocket"]:
                opponent["websocket"].send_message(
                    json.dumps(
                        {"type": "draw_declined", "message": "Draw offer declined"}
                    )
                )
        except Exception as e:
            print(f"Draw decline error: {e}")

    def handle_ws_draw_cancel(self, game, session_id):
        """Handle draw offer cancellation by the sender."""
        try:
            # Notify opponent that draw offer was cancelled
            opponent = (
                game["player2"]
                if game["player1"]["session_id"] == session_id
                else game["player1"]
            )

            if opponent["websocket"]:
                opponent["websocket"].send_message(
                    json.dumps(
                        {"type": "draw_cancelled", "message": "Draw offer cancelled"}
                    )
                )
        except Exception as e:
            print(f"Draw cancel error: {e}")

    def handle_game_end(self, game, reason, winner_color):
        """Handle game completion and ELO updates."""
        global ACTIVE_GAMES

        try:
            p1 = game["player1"]
            p2 = game["player2"]

            def send_game_over(result, elo_changes):
                msg = json.dumps(
                    {
                        "type": "game_over",
                        "winner": result,
                        "reason": reason,
                        "elo_changes": elo_changes,
                    }
                )
                if p1["websocket"]:
                    p1["websocket"].send_message(msg)
                if p2["websocket"]:
                    p2["websocket"].send_message(msg)

            # --- Determine result ---
            if reason in ("checkmate", "resignation"):
                winner = p1 if p1["color"] == winner_color else p2
                loser = p2 if winner is p1 else p1

                winner_score = 1.0
                result = winner_color

            elif reason in ("draw", "stalemate"):
                winner = loser = None
                winner_score = 0.5
                result = "draw"

            else:
                # Fallback: treat unknown reason as draw
                winner = loser = None
                winner_score = 0.5
                result = "draw"

            # --- Calculate ELO ---
            if winner and loser:
                delta = elo_delta(winner["elo"], loser["elo"], winner_score)

                elo_changes = {
                    winner["color"]: delta,
                    loser["color"]: -delta,
                }

                if not (
                    update_player_elo(winner["user_id"], winner["elo"] + delta)
                    and update_player_elo(loser["user_id"], loser["elo"] - delta)
                ):
                    raise DBException(
                        f"Could not update elo! Winner: {winner['user_id']} - Loser: {loser['user_id']} - Change: {delta}"
                    )
                if not record_game_win(winner["user_id"], loser["user_id"]):
                    raise DBException("Could not update wins!")

            else:
                p1_delta = elo_delta(
                    p1["elo"], p2["elo"], winner_score if winner_score else 0.5
                )

                elo_changes = {
                    p1["color"]: p1_delta,
                    p2["color"]: -p1_delta,
                }

                update_player_elo(p1["user_id"], p1["elo"] + p1_delta)
                update_player_elo(p2["user_id"], p2["elo"] - p1_delta)
                record_game_draw(p1["user_id"], p2["user_id"])

            # --- Notify clients ---
            send_game_over(result, elo_changes)

            # --- Cleanup ---
            ACTIVE_GAMES.pop(self.game_id, None)
            print(f"Game {self.game_id} ended: {result} - {reason}")

        except Exception as e:
            print(f"Game end handling error: {e}")
            traceback.print_exc()

    def on_ws_closed(self):
        """Called when WebSocket connection closes."""
        global ACTIVE_GAMES

        try:
            if (
                hasattr(self, "game_id")
                and self.game_id
                and self.game_id in ACTIVE_GAMES
            ):
                game = ACTIVE_GAMES[self.game_id]

                # Clear the websocket reference
                if (
                    game["player1"].get("websocket") == self
                    or game["player2"].get("websocket") == self
                ):
                    if game["player1"].get("websocket") == self:
                        game["player1"]["websocket"] = None
                    if game["player2"].get("websocket") == self:
                        game["player2"]["websocket"] = None

                    print(
                        f"WebSocket disconnected for game {self.game_id} (username: {getattr(self, 'username', 'Unknown')})"
                    )

        except Exception as e:
            print(f"WebSocket close error: {e}")
            traceback.print_exc()

    def session_login(self, user_id: int, username: str) -> None:
        """Create session and set cookie."""
        session_id = SESSION_MANAGER.create_session(
            user_id=user_id,
            username=username,
            ip=self.client_address[0],
        )

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header(
            "Set-Cookie",
            f"session_id={session_id}; Path=/; HttpOnly; SameSite=Strict; Max-Age=3600",
        )
        self.end_headers()

        response = json.dumps(
            {
                "success": True,
                "message": "Login successful",
                "redirect": "/home",
            }
        )
        self.wfile.write(response.encode("utf-8"))


def monitor_server() -> None:
    """
    Monitor server health and handle shutdown.
    """

    def signal_handler(signum, _frame):
        """Handle interrupt signals gracefully."""
        signal_name = signal.Signals(signum).name
        print(f"\n{signal_name} received")
        SERVER_STATE.signal_shutdown(f"{signal_name} received")

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Wait for shutdown signal (blocks efficiently)
        SERVER_STATE.wait_for_shutdown()

        # Check for timeout from HTTP server
        if HTTPD and HTTPD.timeout:
            print("Server inactivity timeout")

        # Check for errors
        if SERVER_STATE.has_error():
            print(f"Server error: {SERVER_STATE.get_error_message()}")

    except Exception as e:
        print(f"Monitor error: {e}")
    finally:
        print("Initiating shutdown sequence...")
        cleanup_resources()


def cleanup_resources() -> None:
    """Clean up all server resources."""
    print("Cleaning up resources...")

    # Stop HTTP server
    if HTTPD:
        try:
            HTTPD.stopping = True
            HTTPD.shutdown()
            HTTPD.server_close()
            print("✓ HTTP server stopped")
        except Exception as e:
            print(f"Error stopping HTTP server: {e}")

    # Close database
    if DB_CONNECTION:
        try:
            DB_CONNECTION.close()
            print("✓ Database closed")
        except Exception as e:
            print(f"Error closing database: {e}")

    # Close session manager
    if SESSION_MANAGER:
        try:
            SESSION_MANAGER.close()
            print("✓ Session manager closed")
        except Exception as e:
            print(f"Error closing session manager: {e}")

    if ENGINE_POOL:
        try:
            ENGINE_POOL.shutdown()
            print("✓ Engine pool closed")
        except Exception as e:
            print(f"Error closing Engine pool: {e}")

    # Log compression statistics
    print("\n")
    if COMPRESSION_CACHE:
        try:
            stats = COMPRESSION_CACHE.get_stats()
            print("\nCompression Statistics:")
            print(f"  Cache hits:   {stats['hits']}")
            print(f"  Cache misses: {stats['misses']}")
            print(f"  Hit rate:     {stats['hit_rate']}")
            print(f"  Compressions: {stats['compressions']}")
            print(
                f"  Cache size:   {stats['cache_size']}/{stats.get('max_cache_size', 'N/A')}"
            )
            COMPRESSION_CACHE.clear_cache()
        except Exception as e:
            print("Error reading/ closing compression pool: {e}")
    print("\n")

    print("Cleanup complete")


def run_http_server(
    ip: str = SERVER_HOST,
    port: int = SERVER_PORT,
    timeout_seconds: int = SERVER_TIMEOUT,
    handler_class=GameHandler,
) -> None:
    """Start and run the HTTP server."""
    global HTTPD

    server_address = (ip, port)

    if CERT_FILE and KEY_FILE:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(
            certfile=CERT_FILE,
            keyfile=KEY_FILE,
        )

        HTTPD = SSLTimeoutThreadingServer(
            server_address=server_address,
            handler_class=handler_class,
            timeout_seconds=timeout_seconds,
            ssl_context=ssl_context,
        )
        print("✓ HTTPS server listening on https://localhost:5000")
    else:
        HTTPD = TimeoutThreadingHTTPServer(
            server_address=server_address,
            handler_class=handler_class,
            timeout_seconds=timeout_seconds,
        )
        print("✓ HTTP server listening on http://localhost:5000")

    try:
        HTTPD.serve_forever()
    except Exception as e:
        if not SERVER_STATE.should_shutdown():
            print(f"HTTP server error: {e}")
            SERVER_STATE.signal_error(f"HTTP server failed: {e}")
    finally:
        SERVER_STATE.signal_shutdown()
        HTTPD.server_close()


if __name__ == "__main__":

    print("=" * 60)
    print("Chess Server Starting (SECURITY HARDENED)")
    print("=" * 60)

    start_time = time.time()

    # Verify game executable exists
    if GAME_HANDLER:
        print(f"✓ Game executable: {GAME_HANDLER}")
    else:
        print("ERROR: No game handler setup")
        sys.exit(1)

    # Setup directory structure
    if SCRIPT_DIR:
        print(f"✓ Working directory: {SCRIPT_DIR}")
    else:
        print("ERROR: Directory setup failed -> Could not locate Script Directory")
        sys.exit(1)

    if FRONTEND_DIR:
        print(f"✓ Frontend directory: {FRONTEND_DIR}")
    else:
        print("ERROR: Directory setup failed -> No Frontend set")
        sys.exit(1)

    # Initialize game database
    if ACTIVE_DB:
        print(f"✓ Game DB Info exists: {ACTIVE_DB}")
    else:
        print("ERROR: Game DB failed to instantiate")
        sys.exit(1)

    # Initialize session manager
    if SESSION_DB:
        print(f"✓ Session manager initialized: {SESSION_DB}")
    else:
        print("ERROR: Session manager failed to instantiate")
        sys.exit(1)

    try:
        ENGINE_POOL = EnginePool(
            GAME_HANDLER,
            SERVER_STATE,
            min_instances=1,
            max_instances=10,
            queue_size=100,
        )
        print("✓ Engine pool initialized")
    except Exception as e:
        print(f"ERROR: Failed to initialize engine pool: {e}")
        sys.exit(1)

    # Start background threads
    print("\nStarting background threads...")
    threads = [
        (
            "HTTP Server",
            run_http_server,
            True,
            [],
        ),
        ("Instance Handler", instance_thread_handler, True, []),
        ("Session Cleanup", cleanup_sessions_loop, True, []),
        ("Matchmaking", matchmaking_loop, True, []),
        ("Init Database", init_database, False, [config["database"]["main"]]),
    ]

    for name, target, daemon, args in threads:
        thread = threading.Thread(target=target, daemon=daemon, name=name, args=args)
        thread.start()
        print(f"✓ Started: {name}")

    startup_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"Server ready in {startup_time:.2f} seconds")
    print(f"{'=' * 60}\n")

    # Monitor server (blocks until shutdown)
    monitor_server()

    print("\nServer shutdown complete")
