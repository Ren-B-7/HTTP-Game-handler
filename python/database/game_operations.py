"""
Game database operations.

This module handles ELO calculations, ELO updates, and game result recording
(wins, losses, draws).

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

import sqlite3
import datetime

import utils.constants as c
from utils.exceptions import DBException
from utils.SanitizeOrValidate import valid_integer


def elo_delta(winner_elo: int, loser_elo: int, score: float, k: int = 32) -> int:
    """
    Calculate ELO change using standard formula.

    The ELO system is a method for calculating the relative skill levels of
    players in zero-sum games. This implementation uses the standard formula
    with configurable K-factor.

    Args:
        winner_elo: Winner's current ELO rating
        loser_elo: Loser's current ELO rating
        score: Game score (1.0 for win, 0.5 for draw, 0.0 for loss)
        k: K-factor controlling rating volatility (default 32)
    """
    expected = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    return int(k * (score - expected))


def update_player_elo(user_id: int, new_elo: int) -> bool:
    """
    Update a player's ELO rating with validation.

    Args:
        user_id: User's database ID
        new_elo: New ELO rating (validated to be between 0-10000)

    Returns:
        True if successful, False otherwise
    """

    if not (c.DB_CONNECTION and c.DB_CURSOR):
        c.SERVER_STATE.signal_error("DB not initialized")
        return False

    try:
        # Validate inputs
        if not valid_integer(user_id, min_val=1):
            raise DBException("Invalid user_id")

        if not valid_integer(new_elo, min_val=0, max_val=10000):
            raise DBException("Invalid ELO value")

        with c.DB_LOCK:
            c.DB_CURSOR.execute(
                "UPDATE users SET elo = ? WHERE user_id = ?",
                (new_elo, user_id),
            )
            c.DB_CONNECTION.commit()
        return True
    except DBException as e:
        print(f"Validation error in update_player_elo: {e}")
        return False
    except sqlite3.Error as e:
        print(f"Error updating ELO: {e}")
        return False


def record_game_win(winner_id: int, loser_id: int) -> bool:
    """
    Record a game win in the database with validation.

    Updates win count for winner, loss count for loser, and last_game
    timestamp for both players.

    Args:
        winner_id: Winner's user ID
        loser_id: Loser's user ID

    Returns:
        True if successful, False otherwise
    """
    if not (c.DB_CONNECTION and c.DB_CURSOR):
        c.SERVER_STATE.signal_error("DB not initialized")
        return False

    try:
        now = datetime.datetime.now().isoformat()

        # Validate IDs
        if not (
            valid_integer(winner_id, min_val=1) and valid_integer(loser_id, min_val=1)
        ):
            raise DBException("Invalid user IDs")

        with c.DB_LOCK:
            # Update winner
            c.DB_CURSOR.execute(
                "UPDATE users SET wins = wins + 1, last_game = ? WHERE user_id = ?",
                (now, winner_id),
            )
            # Update loser
            c.DB_CURSOR.execute(
                "UPDATE users SET losses = losses + 1, last_game = ? WHERE user_id = ?",
                (now, loser_id),
            )
            c.DB_CONNECTION.commit()
        return True
    except DBException as e:
        print(f"Validation error in record_game_win: {e}")
        return False
    except sqlite3.Error as e:
        print(f"Error recording game: {e}")
        return False


def record_game_draw(player1_id: int, player2_id: int) -> bool:
    """
    Record a draw in the database with validation.

    Updates draw count and last_game timestamp for both players.

    Args:
        player1_id: First player's user ID
        player2_id: Second player's user ID

    Returns:
        True if successful, False otherwise
    """
    if not (c.DB_CONNECTION and c.DB_CURSOR):
        c.SERVER_STATE.signal_error("DB not initialized")
        return False

    try:
        now = datetime.datetime.now().isoformat()

        # Validate IDs
        if not (
            valid_integer(player1_id, min_val=1)
            and valid_integer(player2_id, min_val=1)
        ):
            raise DBException("Invalid user IDs")

        with c.DB_LOCK:
            # Update both players
            c.DB_CURSOR.execute(
                "UPDATE users SET draws = draws + 1, last_game = ? WHERE user_id = ?",
                (now, player1_id),
            )
            c.DB_CURSOR.execute(
                "UPDATE users SET draws = draws + 1, last_game = ? WHERE user_id = ?",
                (now, player2_id),
            )
            c.DB_CONNECTION.commit()
        return True
    except DBException as e:
        print(f"Validation error in record_game_draw: {e}")
        return False
    except sqlite3.Error as e:
        print(f"Error recording draw: {e}")
        return False
