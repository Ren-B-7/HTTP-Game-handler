"""
Matchmaking system for chess server.

This module handles the matchmaking queue, player matching, and game creation.

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

import time
import random
import queue
import traceback

import utils.constants as c
from database.user_operations import get_user_stats_by_id


def matchmaking_loop() -> None:
    """
    Continuously checks the matchmaking queue and creates games when two players are waiting.

    This background thread:
    1. Polls the matchmaking queue for new players
    2. Removes stale players (waiting > 5 minutes)
    3. Creates games when =>2 players are waiting
    """

    # Constants
    stale_player_threshold = 300  # 5 minutes
    loop_delay = 0.5  # seconds

    waiting_players = []
    # Add user_ids to set to ensure we dont add the same player twice
    waiting_player_ids = set()

    # Validate server initialization
    if not c.SERVER_STATE:
        print("ERROR: Server not initialized correctly")
        c.SERVER_STATE.should_shutdown()

    if not c.MATCHMAKING_QUEUE:
        print("ERROR: Matchmaking queue not initialized correctly")
        c.SERVER_STATE.should_shutdown()

    while not c.SERVER_STATE.should_shutdown():
        try:
            # Poll queue for new players
            _poll_queue(waiting_players, waiting_player_ids)

            # Clean up stale entries
            _remove_stale_players(
                waiting_players, waiting_player_ids, stale_player_threshold
            )

            # Create games from waiting players
            _create_games_from_queue(waiting_players, waiting_player_ids)

            time.sleep(loop_delay)

        except Exception as e:
            print(f"Matchmaking loop error: {e}")
            traceback.print_exc()
            time.sleep(1)

    print("Matchmaking loop shutting down")


def _poll_queue(waiting_players: list, waiting_player_ids: set) -> None:
    """Add new players from the queue to the waiting list."""

    try:
        player = c.MATCHMAKING_QUEUE.get(timeout=1)

        user_id = player.get("user_id")

        # Deduplicate by user_id (preferred)
        if user_id in waiting_player_ids:
            print(f"Skipping duplicate matchmaking entry for user_id={user_id}")
            return

        player["timestamp"] = time.time()

        waiting_players.append(player)
        waiting_player_ids.add(user_id)

        print(f"Player {player.get('username', 'Unknown')} added to matchmaking queue")

    except queue.Empty:
        pass


def _remove_stale_players(
    waiting_players: list, waiting_player_ids: set, threshold: int
) -> None:
    current_time = time.time()

    kept_players = []
    for p in waiting_players:
        if current_time - p["timestamp"] < threshold:
            kept_players.append(p)
        else:
            waiting_player_ids.discard(p["user_id"])

    removed_count = len(waiting_players) - len(kept_players)
    waiting_players[:] = kept_players

    if removed_count > 0:
        print(f"Removed {removed_count} stale player(s) from queue")


def _create_games_from_queue(waiting_players: list, waiting_player_ids: set) -> None:
    while len(waiting_players) >= 2:
        player1 = waiting_players.pop(0)
        player2 = waiting_players.pop(0)

        waiting_player_ids.discard(player1["user_id"])
        waiting_player_ids.discard(player2["user_id"])

        if not _validate_player_sessions(player1, player2):
            print("Skipping match - invalid session(s)")
            continue

        success = _create_game(player1, player2)

        if not success:
            waiting_players.insert(0, player2)
            waiting_players.insert(0, player1)
            waiting_player_ids.add(player1["user_id"])
            waiting_player_ids.add(player2["user_id"])


def _validate_player_sessions(player1: dict, player2: dict) -> bool:
    """Verify both players have valid sessions."""

    session1 = c.SESSION_MANAGER.get_session(player1["session_id"])
    session2 = c.SESSION_MANAGER.get_session(player2["session_id"])
    return bool(session1 and session2)


def _create_game(player1: dict, player2: dict) -> bool:
    """
    Create a new game between two players and notify them.

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
        c.ACTIVE_GAMES[game_id] = game_state

        # Get initial legal moves
        _initialize_legal_moves(game_id, game_state)

        # Notify both players by storing game_id for their long-polling requests
        c.MATCHMAKING_RESULTS[player1["session_id"]] = {
            "game_id": game_id,
            "notified": False,
        }
        c.MATCHMAKING_RESULTS[player2["session_id"]] = {
            "game_id": game_id,
            "notified": False,
        }

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
    _game_id: str,
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
        if not c.ENGINE_POOL:
            raise Exception("Could not poll engine pool")

        initial_state = c.ENGINE_POOL.submit_task(
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
