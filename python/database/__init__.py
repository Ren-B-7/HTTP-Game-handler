"""
Database package for chess server.
"""

from .connection import init_database
from .user_operations import (
    create_new_user,
    get_username_and_pass,
    get_user_stats_by_id,
    update_username,
    update_password,
    delete_user_account,
    compare_password,
)
from .game_operations import (
    elo_delta,
    update_player_elo,
    record_game_win,
    record_game_draw,
)

__all__ = [
    "init_database",
    "create_new_user",
    "get_username_and_pass",
    "get_user_stats_by_id",
    "update_username",
    "update_password",
    "delete_user_account",
    "compare_password",
    "elo_delta",
    "update_player_elo",
    "record_game_win",
    "record_game_draw",
]
