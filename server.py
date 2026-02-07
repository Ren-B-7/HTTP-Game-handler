"""
Chess server implementation with WebSocket support, session management, and game logic.

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

# Thread/ program
import os
import signal
import sys
import threading
import traceback
import time
from typing import Dict, Optional, Tuple

# Http server
import hashlib

# Database
import sqlite3
import datetime

# Game
import json
import random
import queue

# Config
from pathlib import Path

from SessionManager import SessionManager
from ThreadedHttpServer import TimeoutThreadingHTTPServer
from HttpSocketHandler import NoDataException, ThreadedHandlerWithSockets
from ServerState import ServerState
from config import load_config, resolve_path
from EngineHandler import EnginePool, InstanceInoperable

# Import constants and exceptions
from constants import (
    config,
    SCRIPT_DIR,
    FRONTEND_DIR,
    SERVER_HOST,
    SERVER_PORT,
    SERVER_TIMEOUT,
    BOT_CLI,
    GAME_HANDLER,
    ACTIVE_DB,
    SESSION_DB,
    SERVER_STATE,
    PROMISCUOUS_IPS,
    SESSION_TIMEOUT,
    SESSION_CACHE_SIZE,
    SESSION_MANAGER,
    ACTIVE_GAMES,
    MATCHMAKING_QUEUE,
    DB_CONNECTION,
    DB_CURSOR,
    DB_LOCK,
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
)

from exceptions import (
    MajorServerSideException,
    DBException,
    ProcessingError,
)


class GameHandler(ThreadedHandlerWithSockets):
    """HTTP/WebSocket handler with authentication and game logic."""

    game_id = None

    def check_auth(self) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
        """
        Check if user is authenticated.

        Returns:
            tuple: (is_authenticated, session_id, username, user_id)
        """
        session_id = self.get_cookie("session_id")

        if not session_id:
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

        # Normal HTTP GET routes
        if self.path == "/":
            return self.redirect("/login")
        if self.path == "/login":
            return self.serve_login()
        if self.path == "/register":
            return self.serve_register()
        if "static" in self.path:
            return self.serve_file()
        if (self.path in ICON_FILES) or ("icons" in self.path):
            return self.serve_icons(str(ICONS_DIRECTORY))

        # Auth check for protected routes
        is_auth, _, _, _ = self.check_auth()
        if not is_auth:
            return self.redirect("/login")

        # Authenticated routes
        if self.path == "/stats":
            return self.serve_stats()
        if self.path == "/game":
            return self.serve_game()
        if self.path == "/home":
            return self.serve_home()
        if self.path == "/profile":
            return self.serve_profile()
        self.send_error(404, "NotFound", f"Page not found: {self.path}")

    def serve_login(self) -> None:
        try:
            self.serve_page(self.read_html(str(LOGIN_HTML)))
        except Exception as e:
            self.send_error(404, "ErrLoginPage", f"Error loading login page: {e}")

    def serve_register(self) -> None:
        try:
            self.serve_page(self.read_html(str(REGISTER_HTML)))
        except Exception as e:
            self.send_error(404, "ErrRegisterPage", f"Error loading register page: {e}")

    def serve_stats(self) -> None:
        try:
            self.serve_page(self.read_html(str(STATS_HTML)))
        except Exception as e:
            self.send_error(404, "ErrStatsPage", f"Error loading stats page: {e}")

    def serve_game(self) -> None:
        try:
            self.serve_page(self.read_html(str(GAME_HTML)))
        except Exception as e:
            self.send_error(404, "ErrGamePage", f"Error loading game page: {e}")

    def serve_home(self) -> None:
        try:
            self.serve_page(self.read_html(str(HOME_HTML)))
        except Exception as e:
            self.send_error(404, "ErrHomePage", f"Error loading home page: {e}")

    def serve_profile(self) -> None:
        try:
            self.serve_page(self.read_html(str(PROFILE_HTML)))
        except Exception as e:
            self.send_error(404, "ErrProfilePage", f"Error loading profile page: {e}")

    def do_POST(self) -> None:
        """Handle all POST requests to the server."""
        if self.path == "/login":
            self.handle_login()
        if self.path == "/register":
            self.handle_register()
        if self.path == "/session":
            self.handle_session()
        if self.path == "/home/search":
            self.handle_search()
        if self.path == "/home/cancel":
            self.handle_cancel_search()
        if self.path == "/stats":
            self.handle_stats()
        if self.path == "/profile/update-username":
            self.handle_change_username()
        if self.path == "/profile/update-password":
            self.handle_change_password()
        if self.path == "/profile/delete-account":
            self.handle_delete_account()
        if self.path == "/logout":
            self.handle_logout()

    def handle_login(self) -> None:
        """Handle user login."""
        try:
            data = self.read_post_request()
            if not data:
                raise NoDataException("No data to be read")
            username = data.get("username", "")
            password = data.get("password", "")

            if not username or not password:
                raise ProcessingError("Missing credentials", 400)

            # Get user data from database
            user_data = get_username_and_pass(username)

            if not user_data:
                raise ProcessingError("Invalid username or password", 401)

            # Verify password
            if not decypher_password(
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
        """Handle user registration."""
        try:
            data = self.read_post_request()
            if not data:
                raise ProcessingError("No data received", 400)

            username = data.get("username", "")
            password = data.get("password", "")
            confirm_password = data.get("confirm_password", "")

            # Validation
            if not username or not password:
                raise ProcessingError("Missing required fields", 400)

            if password != confirm_password:
                raise ProcessingError("Passwords do not match", 400)

            if len(username) < 3:
                raise ProcessingError("Username must be at least 3 characters", 400)

            if len(password) < 6:
                raise ProcessingError("Password must be at least 6 characters", 400)

            # Create user
            user_id = create_new_user(username, password)
            if user_id:
                self.session_login(user_id=user_id, username=username)
            else:
                raise ProcessingError("Username already exists", 409)
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

            stats = get_user_stats(username)
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
        if session_id:
            SESSION_MANAGER.delete_session(session_id)
        self.json_success(message="Logged out successfully")

    def handle_change_username(self) -> None:
        """Handle username change request."""
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

            if not new_username or not password:
                raise ProcessingError("Missing credentials", 400)
            if len(new_username) < 3:
                raise ProcessingError("Username must be at least 3 characters", 400)
            if len(new_username) > 20:
                raise ProcessingError("Username must be at most 20 characters", 400)

            # Verify existing credentials
            user_data = get_username_and_pass(username)
            if not user_data:
                raise ProcessingError("Invalid username or password", 401)
            if not decypher_password(
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
        """Handle password change request."""
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

            if not (current_password and new_password):
                raise ProcessingError("Current and new passwords are required", 400)
            if new_password != confirm_password:
                raise ProcessingError("Passwords don't match", 400)
            if len(new_password) < 6:
                raise ProcessingError("New password must be at least 6 characters", 400)

            # Verify current password
            user_data = get_username_and_pass(username)
            if not user_data:
                raise ProcessingError("User not found", 404)
            if not decypher_password(
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

            # Verify password
            user_data = get_username_and_pass(username)
            if not user_data:
                raise ProcessingError("User not found", 404)

            if not decypher_password(
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
            self.json_error("Error deleting account", 500)

    def session_login(self, user_id: int, username: str) -> None:
        """Create session and send success response."""
        client_ip = self.client_address[0]
        session_id = SESSION_MANAGER.create_session(user_id, username, client_ip)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header(
            "Set-Cookie",
            f"session_id={session_id}; Path=/; HttpOnly; SameSite=Strict; Max-Age=86400",
        )
        self.end_headers()

        response = json.dumps({"success": True, "message": "Login successful"})
        self.wfile.write(response.encode("utf-8"))

    def handle_search(self) -> None:
        """Handle matchmaking search request."""
        is_auth, session_id, username, user_id = self.check_auth()
        try:
            if not is_auth:
                raise ProcessingError("Not authenticated", 401)
            if not (session_id and username and user_id):
                raise ProcessingError("Could not retrieve user info", 500)
        except ProcessingError as e:
            self.json_error(e.message, e.code)
        else:
            # Add to matchmaking queue with user_id
            MATCHMAKING_QUEUE.put(
                {"username": username, "user_id": user_id, "session_id": session_id}
            )
            self.json_success(message="Added to matchmaking queue")

    def handle_cancel_search(self) -> None:
        """Handle matchmaking cancellation."""
        is_auth, session_id, username, user_id = self.check_auth()
        try:
            if not is_auth:
                raise ProcessingError("Not authenticated", 401)
            if not (session_id and username and user_id):
                raise ProcessingError("Could not retrieve user info", 500)
        except ProcessingError as e:
            self.json_error(e.message, e.code)
        else:
            # Remove from queue (simplified - full implementation would track better)
            self.json_success(message="Removed from matchmaking queue")

    def handle_stats(self) -> None:
        """Handle stats request."""
        try:
            is_auth, session_id, username, user_id = self.check_auth()

            if not is_auth:
                raise ProcessingError("Not authenticated", 401)
            if not (session_id and username and user_id):
                raise ProcessingError("Could not retrieve user info", 500)

            stats = get_user_stats(username)
            if not stats:
                raise ProcessingError("Stats not found", 404)
            payload = {
                "username": username,
                "elo": stats["elo"],
                "wins": stats["wins"],
                "draws": stats["draws"],
                "losses": stats["losses"],
                "last_game": stats["last_game"],
                "date_joined": stats["join_date"],
            }

            if payload:
                self.json_success(data=payload)
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
                if (
                    game_data["player1"]["session_id"] == session_id
                    or game_data["player2"]["session_id"] == session_id
                ):
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
            import traceback

            traceback.print_exc()
            self.send_message(
                json.dumps({"type": "error", "message": "Connection error"})
            )
            self._ws_close()

    def on_ws_message(self, message):
        """Called when a message is received via WebSocket."""
        global ACTIVE_GAMES

        try:
            data = json.loads(message)
            msg_type = data.get("type")

            # Get and validate session
            session_id = self.get_cookie("session_id")
            if not session_id:
                self.send_message(
                    json.dumps({"type": "error", "message": "Not authenticated"})
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
                # Support both formats:
                # 1. {"type": "move", "move": "e2e4"} - UCI format
                # 2. {"type": "move", "from": "e2", "to": "e4"} - separate fields
                move_str = data.get("move")
                from_sq = data.get("from")
                to_sq = data.get("to")

                if move_str:
                    # Parse UCI format (e2e4) into from/to
                    if len(move_str) >= 4:
                        from_sq = move_str[:2]
                        to_sq = move_str[2:4]

                self.handle_ws_move(game, username, session_id, from_sq, to_sq)

            elif msg_type == "resign":
                self.handle_ws_resign(game, username, session_id)

            elif msg_type == "offer_draw":
                self.handle_ws_draw_offer(game, username, session_id)

            elif msg_type == "draw_accept":
                self.handle_ws_draw_accept(game, username, session_id)

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

    def handle_ws_move(self, game, username, session_id, from_sq, to_sq):
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

            # Format move - support both UCI format (e2e4) and hyphenated (e2-e4)
            if from_sq and to_sq:
                # Message has separate from/to fields
                move = f"{from_sq}-{to_sq}"
            else:
                # Try to get move from data
                move = None

            if not move:
                self.send_message(
                    json.dumps({"type": "error", "message": "Invalid move format"})
                )
                return

            # Send to chess engine
            engine_request = {"reason": "move", "fen": game["fen"], "moves": move}

            response = ENGINE_POOL.submit_task(game["instance"], engine_request)

            if not response:
                raise InstanceInoperable("Could not read from engine pool")

            if response.get("message") == "valid":
                # Update game state
                game["fen"] = response["fen"]
                game["moves"].append(move)
                game["legal_moves"] = response.get("possible_moves", [])
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
                        "type": "move_update",  # Changed from "game_state" for consistency
                        "fen": game["fen"],
                        "next_turn": game["current_turn"],  # Changed from "turn"
                        "legal_moves": game["legal_moves"],
                        "last_move": move,
                        "move_history": game["moves"],  # Add full move history
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
            import traceback

            traceback.print_exc()
            self.send_message(
                json.dumps({"type": "error", "message": "Move processing error"})
            )

    def handle_ws_resign(self, game, username, session_id):
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

    def handle_ws_draw_accept(self, game, username, session_id):
        """Handle draw acceptance."""
        try:
            self.handle_game_end(game, "draw", None)
        except Exception as e:
            print(f"Draw accept error: {e}")

    def handle_game_end(self, game, reason, winner_color):
        """Handle game completion."""
        global ACTIVE_GAMES

        try:
            # Determine result
            if reason == "checkmate" or reason == "resignation":
                result = winner_color  # "white" or "black"
                winner = (
                    game["player1"]
                    if game["player1"]["color"] == winner_color
                    else game["player2"]
                )
                loser = (
                    game["player2"] if winner == game["player1"] else game["player1"]
                )

                # Calculate ELO changes
                winner_new_elo = update_elo(winner["elo"], loser["elo"], 1.0)
                loser_new_elo = update_elo(loser["elo"], winner["elo"], 0.0)

                elo_changes = {
                    winner["color"]: int(winner_new_elo - winner["elo"]),
                    loser["color"]: int(loser_new_elo - loser["elo"]),
                }

                # Update database using user_id
                update_player_elo(winner["user_id"], winner_new_elo)
                update_player_elo(loser["user_id"], loser_new_elo)
                record_game_win(winner["user_id"], loser["user_id"])

            elif reason == "draw" or reason == "stalemate":
                # Draw
                result = "draw"
                player1_new_elo = update_elo(
                    game["player1"]["elo"], game["player2"]["elo"], 0.5
                )
                player2_new_elo = update_elo(
                    game["player2"]["elo"], game["player1"]["elo"], 0.5
                )

                elo_changes = {
                    game["player1"]["color"]: int(
                        player1_new_elo - game["player1"]["elo"]
                    ),
                    game["player2"]["color"]: int(
                        player2_new_elo - game["player2"]["elo"]
                    ),
                }

                # Update database using user_id
                update_player_elo(game["player1"]["user_id"], player1_new_elo)
                update_player_elo(game["player2"]["user_id"], player2_new_elo)
                record_game_draw(game["player1"]["user_id"], game["player2"]["user_id"])
            else:
                # Unknown reason - treat as draw
                result = "draw"
                elo_changes = {}

            # Send game over message (matches client expectations)
            end_message = json.dumps(
                {
                    "type": "game_over",  # Changed from "game_end"
                    "winner": result,
                    "reason": reason,
                    "elo_changes": elo_changes,
                }
            )

            if game["player1"]["websocket"]:
                game["player1"]["websocket"].send_message(end_message)
            if game["player2"]["websocket"]:
                game["player2"]["websocket"].send_message(end_message)

            # Cleanup

            if self.game_id in ACTIVE_GAMES:
                del ACTIVE_GAMES[self.game_id]

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
                and (self.game_id in ACTIVE_GAMES)
            ):
                game = ACTIVE_GAMES[self.game_id]

                # Determine which player disconnected
                is_player1 = (
                    hasattr(self, "user_id")
                    and game["player1"]["user_id"] == self.user_id
                )

                # Notify opponent of disconnection
                if game["status"] == "ongoing":
                    opponent = game["player2"] if is_player1 else game["player1"]
                    if opponent.get("websocket") and opponent["websocket"].connected:
                        opponent["websocket"].send_message(
                            json.dumps(
                                {
                                    "type": "opponent_disconnected",
                                    "message": f"{self.username if hasattr(self, 'username') else 'Opponent'} has disconnected",
                                }
                            )
                        )

                    # Award win to remaining player
                    game["status"] = "finished"
                    game["winner"] = opponent["color"]

                # Clear websocket references
                if game["player1"]["websocket"] == self:
                    game["player1"]["websocket"] = None
                if game["player2"]["websocket"] == self:
                    game["player2"]["websocket"] = None

                print(f"WebSocket closed for game {self.game_id}")

        except Exception as e:
            print(f"WebSocket close error: {e}")
            traceback.print_exc()

    def start_websocket_ping(self):
        """Start periodic ping to keep WebSocket alive and detect disconnects."""

        def ping_loop():
            while self.connected and hasattr(self, "game_id"):
                try:
                    time.sleep(30)  # Ping every 30 seconds
                    if self.connected:
                        self.send_message(json.dumps({"type": "ping"}))
                except Exception as e:
                    print(f"Ping error: {e}")
                    break

        ping_thread = threading.Thread(target=ping_loop, daemon=True)
        ping_thread.start()


# ELO and Game Recording Functions


def update_elo(player_elo: int, opponent_elo: int, score: float) -> float:
    """
    Calculate new ELO rating using the standard ELO formula.

    Args:
        player_elo: Current player ELO
        opponent_elo: Opponent's ELO
        score: Game result (1.0 = win, 0.5 = draw, 0.0 = loss)

    Returns:
        New ELO rating for the player

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    k = 32  # ELO K-factor

    expected_score = 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))
    new_elo = player_elo + k * (score - expected_score)

    return new_elo


def update_player_elo(user_id: int, new_elo: float) -> bool:
    """
    Update a player's ELO in the database.

    Args:
        user_id: Player's user ID
        new_elo: New ELO rating

    Returns:
        True if successful, False otherwise

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    global DB_CONNECTION, DB_CURSOR, DB_LOCK

    if not (DB_CONNECTION and DB_CURSOR):
        SERVER_STATE.signal_error("DB not initialized")
        return False

    try:
        with DB_LOCK:
            DB_CURSOR.execute(
                "UPDATE users SET elo = ? WHERE user_id = ?",
                (new_elo, user_id),
            )
            DB_CONNECTION.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error updating ELO for user_id {user_id}: {e}")
        return False


def record_game_win(winner_id: int, loser_id: int) -> bool:
    """
    Record a game win in the database.

    Args:
        winner_id: User ID of winner
        loser_id: User ID of loser

    Returns:
        True if successful, False otherwise

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    global DB_CONNECTION, DB_CURSOR, DB_LOCK

    if not (DB_CONNECTION and DB_CURSOR):
        SERVER_STATE.signal_error("DB not initialized")
        return False

    try:
        now = datetime.datetime.now().isoformat()
        with DB_LOCK:
            # Update winner
            DB_CURSOR.execute(
                "UPDATE users SET wins = wins + 1, last_game = ? WHERE user_id = ?",
                (now, winner_id),
            )
            # Update loser
            DB_CURSOR.execute(
                "UPDATE users SET losses = losses + 1, last_game = ? WHERE user_id = ?",
                (now, loser_id),
            )
            DB_CONNECTION.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error recording game: {e}")
        return False


def record_game_draw(player1_id: int, player2_id: int) -> bool:
    """
    Record a draw in the database.

    Args:
        player1_id: First player's user ID
        player2_id: Second player's user ID

    Returns:
        True if successful, False otherwise

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    global DB_CONNECTION, DB_CURSOR, DB_LOCK

    if not (DB_CONNECTION and DB_CURSOR):
        SERVER_STATE.signal_error("DB not initialized")
        return False

    try:
        now = datetime.datetime.now().isoformat()
        with DB_LOCK:
            # Update both players
            DB_CURSOR.execute(
                "UPDATE users SET draws = draws + 1, last_game = ? WHERE user_id = ?",
                (now, player1_id),
            )
            DB_CURSOR.execute(
                "UPDATE users SET draws = draws + 1, last_game = ? WHERE user_id = ?",
                (now, player2_id),
            )
            DB_CONNECTION.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error recording draw: {e}")
        return False


def init_database(db_name: str) -> None:
    global DB_CONNECTION, DB_CURSOR

    db_path = resolve_path(SCRIPT_DIR, db_name)

    try:
        DB_CONNECTION = sqlite3.connect(
            db_path,
            check_same_thread=False,
            isolation_level=None,  # autocommit (optional but useful)
        )
        DB_CURSOR = DB_CONNECTION.cursor()

        with DB_LOCK:
            DB_CURSOR.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    elo INTEGER NOT NULL DEFAULT 500,
                    wins INTEGER NOT NULL DEFAULT 0,
                    draws INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    join_date TEXT NOT NULL,
                    last_game TEXT
                )
            """)

        print(f"✓ Database initialized: {db_path}")

    except Exception as e:
        SERVER_STATE.signal_error(f"Database initialization failed: {e}")


def get_username_and_pass(username: str) -> Optional[Dict]:
    """Get user credentials and user_id from database."""
    if not (DB_CONNECTION and DB_CURSOR):
        SERVER_STATE.signal_error("DB not initialized")
        return None

    try:
        with DB_LOCK:
            DB_CURSOR.execute(
                "SELECT user_id, password_hash, salt FROM users WHERE username = ?",
                (username,),
            )
            row = DB_CURSOR.fetchone()

        if not row:
            return None

        return {"user_id": row[0], "password_hash": row[1], "salt": row[2]}
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None


def get_user_stats(username: str) -> Dict:
    """Get user statistics from database."""
    if not (DB_CONNECTION and DB_CURSOR):
        SERVER_STATE.signal_error("DB not initialized")
        return {}

    try:
        with DB_LOCK:
            DB_CURSOR.execute("SELECT * FROM users WHERE username = ?", (username,))
            user_data = DB_CURSOR.fetchone()

        if not user_data:
            return {}

        return {
            "elo": user_data[4],
            "wins": user_data[5],
            "draws": user_data[6],
            "losses": user_data[7],
            "join_date": user_data[8],
            "last_game": user_data[9],
        }
    except sqlite3.Error as e:
        print(f"Error: {e}")
        return {}


def get_user_stats_by_id(user_id: int) -> Dict:
    """
    Get user statistics from database by user_id.

    Args:
        user_id: User's ID

    Returns:
        Dict with user stats or empty dict if not found
    """
    if not (DB_CONNECTION and DB_CURSOR):
        SERVER_STATE.signal_error("DB not initialized")
        return {}

    try:
        with DB_LOCK:
            DB_CURSOR.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user_data = DB_CURSOR.fetchone()

        if not user_data:
            return {}

        return {
            "elo": user_data[4],
            "wins": user_data[5],
            "draws": user_data[6],
            "losses": user_data[7],
            "join_date": user_data[8],
            "last_game": user_data[9],
        }
    except sqlite3.Error as e:
        print(f"Error: {e}")
        return {}


def create_new_user(name: str, password: str) -> Optional[int]:
    """
    Insert a new user into the database.

    Returns:
        The new user's user_id if successful, None otherwise
    """
    if not (DB_CONNECTION and DB_CURSOR):
        SERVER_STATE.signal_error("DB not initialized")
        return None

    try:
        password_hash, salt = generate_password_hash(password)
        with DB_LOCK:
            DB_CURSOR.execute(
                """
                INSERT INTO users (username, password_hash, salt, elo, wins, draws, losses, join_date, last_game)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    password_hash,
                    salt,
                    500,
                    0,
                    0,
                    0,
                    datetime.datetime.now().isoformat(),
                    None,
                ),
            )
            DB_CONNECTION.commit()
            user_id = DB_CURSOR.lastrowid
        print(f"User {name} added successfully!")
        return user_id
    except sqlite3.IntegrityError:
        return None


def generate_password_hash(password: str, salt: Optional[bytes] = None) -> tuple:
    """
    Generate a SHA512 hash of the given password and an optional salt.

    Returns a tuple containing the hashed password and the salt as hexadecimal strings.
    """
    if not salt:
        salt = os.urandom(16)
    hash_obj = hashlib.sha512(salt + password.encode())
    hashed_password = hash_obj.hexdigest()
    return hashed_password, salt.hex()


def decypher_password(password: str, hashed_password: str, salt: str) -> bool:
    """Verify a password against a hash."""
    return generate_password_hash(password, bytes.fromhex(salt))[0] == hashed_password


def update_username(user_id: int, new_username: str) -> bool:
    """
    Update a user's username in the database.

    Args:
        user_id: User's ID (immutable identifier)
        new_username: New username to set

    Returns:
        True if successful, False if username already exists or error occurs

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    if not (DB_CONNECTION and DB_CURSOR):
        SERVER_STATE.signal_error("DB not initialized")
        return False

    try:
        with DB_LOCK:
            # Check if new username already exists
            DB_CURSOR.execute(
                "SELECT user_id FROM users WHERE username = ?",
                (new_username,),
            )
            if DB_CURSOR.fetchone():
                return False

            # Update username
            DB_CURSOR.execute(
                "UPDATE users SET username = ? WHERE user_id = ?",
                (new_username, user_id),
            )
            DB_CONNECTION.commit()

        print(f"Username updated for user_id {user_id} -> {new_username}")
        return True
    except sqlite3.Error as e:
        print(f"Error updating username: {e}")
        return False


def update_password(user_id: int, new_password: str) -> bool:
    """
    Update a user's password in the database.

    Args:
        user_id: User's ID
        new_password: New password (plain text, will be hashed)

    Returns:
        True if successful, False otherwise

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """

    if not (DB_CONNECTION and DB_CURSOR):
        SERVER_STATE.signal_error("DB not initialized")
        return False

    try:
        # Generate new password hash and salt
        password_hash, salt = generate_password_hash(new_password)

        with DB_LOCK:
            DB_CURSOR.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE user_id = ?",
                (password_hash, salt, user_id),
            )
            DB_CONNECTION.commit()

        print(f"Password updated for user_id: {user_id}")
        return True
    except sqlite3.Error as e:
        print(f"Error updating password: {e}")
        return False


def delete_user_account(user_id: int) -> bool:
    """
    Delete a user account from the database.

    Args:
        user_id: User ID of account to delete

    Returns:
        True if successful, False otherwise

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """

    if not (DB_CONNECTION and DB_CURSOR):
        SERVER_STATE.signal_error("DB not initialized")
        return False

    try:
        with DB_LOCK:
            DB_CURSOR.execute(
                "DELETE FROM users WHERE user_id = ?",
                (user_id,),
            )
            DB_CONNECTION.commit()

        print(f"Account deleted: {user_id}")
        return True
    except sqlite3.Error as e:
        print(f"Error deleting account: {e}")
        return False


def cleanup_sessions_loop() -> None:
    """Background loop that periodically removes expired user sessions.

    This function runs as a daemon in a separate thread, continuously cleaning
    up stale sessions that have exceeded their validity period. It checks the
    global SERVER_STATE for shutdown signals and exits gracefully when requested.

    The loop uses a 60-second wait between cleanup cycles for efficient resource
    usage while maintaining responsive shutdown behavior.
    """
    while not SERVER_STATE.should_shutdown():
        try:
            SESSION_MANAGER.cleanup_expired_sessions()
            # Use wait instead of sleep for faster shutdown response
            if SERVER_STATE.wait_for_shutdown(timeout=60):
                break
        except Exception as e:
            print(f"Session cleanup error: {e}")
            time.sleep(10)


def instance_thread_handler() -> None:
    """
    NEW: Manages engine pool auto-scaling and game cleanup.
    Replaces the old per-game instance management.

    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """
    global ACTIVE_GAMES, ENGINE_POOL

    while not SERVER_STATE.should_shutdown():
        try:
            # Auto-scale engine pool
            if ENGINE_POOL:
                ENGINE_POOL.auto_scale()

            # Clean up finished games
            games_to_remove = []

            for game_id, game_data in list(ACTIVE_GAMES.items()):
                # Check for timeout (30 minutes of inactivity)
                if time.time() - game_data.get("last_move_at", time.time()) > 1800:
                    print(f"Game {game_id}: Timeout - no activity for 30 minutes")
                    games_to_remove.append(game_id)
                    continue

                # Check if game is finished
                if game_data.get("status") == "finished":
                    games_to_remove.append(game_id)

            # Clean up finished games
            for game_id in games_to_remove:
                if game_id in ACTIVE_GAMES:
                    del ACTIVE_GAMES[game_id]
                    print(f"Cleaned up game {game_id}")

            # Print stats every 30 seconds
            if int(time.time()) % 30 == 0:
                stats = ENGINE_POOL.get_stats() if ENGINE_POOL else {}
                print(
                    f"Pool stats: {stats.get('instance_count', 0)} instances, {len(ACTIVE_GAMES)} active games"
                )

            time.sleep(5)  # Check every 5 seconds

        except Exception as e:
            print(f"Instance handler error: {e}")
            traceback.print_exc()
            time.sleep(5)


def matchmaking_loop() -> None:
    """
    Continuously checks the matchmaking queue and creates games when two players are waiting.

    Monitors the queue for available players, validates their sessions, and pairs them
    into games with randomized colors. Automatically removes stale queue entries.

    Author: Renier Barnard (renier52147@gmail.com / renierb@axxess.co.za)
    """
    global MATCHMAKING_QUEUE, ACTIVE_GAMES, ENGINE_POOL

    # Constants
    QUEUE_TIMEOUT = 1  # seconds
    STALE_PLAYER_THRESHOLD = 300  # 5 minutes
    LOOP_DELAY = 0.5  # seconds
    INITIAL_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    waiting_players = []

    # Validate server initialization
    if not SERVER_STATE:
        print("ERROR: Server not initialized correctly")
        sys.exit(1)

    if not MATCHMAKING_QUEUE:
        print("ERROR: Matchmaking queue not initialized correctly")
        sys.exit(1)

    while not SERVER_STATE.should_shutdown():
        try:
            # Poll queue for new players
            _poll_queue(waiting_players)

            # Clean up stale entries
            _remove_stale_players(waiting_players, STALE_PLAYER_THRESHOLD)

            # Create games from waiting players
            _create_games_from_queue(waiting_players)

            time.sleep(LOOP_DELAY)

        except Exception as e:
            print(f"Matchmaking loop error: {e}")
            traceback.print_exc()
            time.sleep(1)

    print("Matchmaking loop shutting down")


def _poll_queue(waiting_players: list) -> None:
    """Add new players from the queue to the waiting list."""
    try:
        player = MATCHMAKING_QUEUE.get(timeout=1)
        player["timestamp"] = time.time()
        waiting_players.append(player)
        print(f"Player {player.get('username', 'Unknown')} added to matchmaking queue")
    except queue.Empty:
        pass


def _remove_stale_players(waiting_players: list, threshold: int) -> None:
    """Remove players who have been waiting longer than the threshold."""
    current_time = time.time()
    initial_count = len(waiting_players)
    waiting_players[:] = [
        p for p in waiting_players if current_time - p["timestamp"] < threshold
    ]
    removed_count = initial_count - len(waiting_players)
    if removed_count > 0:
        print(f"Removed {removed_count} stale player(s) from queue")


def _create_games_from_queue(waiting_players: list) -> None:
    """Create games while there are at least 2 players waiting."""
    while len(waiting_players) >= 2:
        player1 = waiting_players.pop(0)
        player2 = waiting_players.pop(0)

        # Validate sessions
        if not _validate_player_sessions(player1, player2):
            print(f"Skipping match - invalid session(s)")
            continue

        # Attempt to create the game
        success = _create_game(player1, player2)

        # Return players to queue if creation failed
        if not success:
            waiting_players.insert(0, player2)
            waiting_players.insert(0, player1)


def _validate_player_sessions(player1: dict, player2: dict) -> bool:
    """Verify both players have valid sessions."""
    session1 = SESSION_MANAGER.get_session(player1["session_id"])
    session2 = SESSION_MANAGER.get_session(player2["session_id"])
    return bool(session1 and session2)


def _create_game(player1: dict, player2: dict) -> bool:
    """
    Create a new game between two players.

    Returns:
        bool: True if game created successfully, False otherwise
    """
    try:
        game_id = _generate_game_id()

        # Fetch player statistics
        player1_stats = get_user_stats_by_id(player1["user_id"])
        player2_stats = get_user_stats_by_id(player2["user_id"])

        # Randomly assign colors
        colors = _assign_colors()

        # Initialize game state
        game_state = _initialize_game_state(
            game_id, player1, player2, player1_stats, player2_stats, colors
        )

        # Store game
        ACTIVE_GAMES[game_id] = game_state

        # Get initial legal moves
        _initialize_legal_moves(game_id, game_state)

        # Log game creation
        print(f"✓ Game {game_id} created:")
        print(f"  {player1['username']} ({player1_stats['elo']}) plays {colors[0]}")
        print(f"  {player2['username']} ({player2_stats['elo']}) plays {colors[1]}")

        return True

    except Exception as e:
        print(f"✗ Failed to create game: {e}")
        traceback.print_exc()
        return False


def _generate_game_id() -> str:
    """Generate a unique game identifier."""
    return f"game_{int(time.time())}_{random.randint(1000, 9999)}"


def _assign_colors() -> tuple:
    """Randomly assign white and black colors to players."""
    colors = ["white", "black"]
    random.shuffle(colors)
    return colors[0], colors[1]


def _initialize_game_state(
    game_id: str,
    player1: dict,
    player2: dict,
    player1_stats: dict,
    player2_stats: dict,
    colors: tuple,
) -> dict:
    """Create the initial game state dictionary."""
    current_time = time.time()

    return {
        "player1": {
            "user_id": player1["user_id"],
            "username": player1["username"],
            "session_id": player1["session_id"],
            "color": colors[0],
            "websocket": None,
            "elo": player1_stats["elo"],
        },
        "player2": {
            "user_id": player2["user_id"],
            "username": player2["username"],
            "session_id": player2["session_id"],
            "color": colors[1],
            "websocket": None,
            "elo": player2_stats["elo"],
        },
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "moves": [],
        "current_turn": "white",
        "legal_moves": [],
        "status": "ongoing",
        "winner": None,
        "created_at": current_time,
        "last_move_at": current_time,
    }


def _initialize_legal_moves(game_id: str, game_state: dict) -> None:
    """Calculate and store initial legal moves for the game."""
    try:
        if not EnginePool:
            raise Exception("Could not poll engine pool")

        initial_state = ENGINE_POOL.submit_task(
            game_id,
            {
                "reason": "validate",
                "fen": game_state["fen"],
                "moves": "",
            },
        )

        if initial_state:
            game_state["legal_moves"] = initial_state.get("possible_moves", [])
    except Exception as e:
        print(f"Warning: Failed to initialize legal moves for {game_id}: {e}")


def monitor_server() -> None:
    """
    Monitor server health and handle shutdown.
    Replaces the old server_error_handler with cleaner event-based approach.
    """
    global HTTPD

    def signal_handler(signum, frame):
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
    global HTTPD, DB_CONNECTION, ENGINE_POOL

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

    print("Cleanup complete")


def run_http_server(
    ip: str,
    port: int,
    timeout_seconds: int,
    server_class=TimeoutThreadingHTTPServer,
    handler_class=GameHandler,
) -> None:
    """Start and run the HTTP server."""
    global HTTPD

    server_address = (ip, port)
    HTTPD = server_class(server_address, handler_class, timeout_seconds=timeout_seconds)

    print("✓ HTTP server listening on port 5000")

    try:
        HTTPD.serve_forever()
    except Exception as e:
        if not SERVER_STATE.should_shutdown():
            print(f"HTTP server error: {e}")
            SERVER_STATE.signal_error(f"HTTP server failed: {e}")
    finally:
        SERVER_STATE.signal_shutdown()
        HTTPD.server_close()


def main():
    """Main entry point with improved startup sequence."""
    global ENGINE_POOL

    print("=" * 60)
    print("Chess Server Starting")
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
            [SERVER_HOST, SERVER_PORT, SERVER_TIMEOUT],
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


if __name__ == "__main__":
    main()
