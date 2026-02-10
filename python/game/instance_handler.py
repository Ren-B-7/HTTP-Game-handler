"""
Game instance management and cleanup.

This module handles engine pool auto-scaling and cleanup of finished/inactive games.

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

import time
import traceback
import utils.constants as c


def instance_thread_handler() -> None:
    """
    Manages engine pool with auto-scaling and game cleanup.

    This background thread performs two main functions:
    1. Auto-scales the engine pool based on demand
    2. Cleans up finished or timed-out games

    Game cleanup criteria:
    - Games with status "finished"
    - Games with no activity for 30 minutes (timeout)

    Runs every 5 seconds and prints stats every 30 seconds.
    """

    while not c.SERVER_STATE.should_shutdown():
        try:
            # Auto-scale engine pool
            if c.ENGINE_POOL:
                c.ENGINE_POOL.auto_scale()

            # Clean up finished games
            games_to_remove = []

            for game_id, game_data in list(c.ACTIVE_GAMES.items()):
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
                if game_id in c.ACTIVE_GAMES:
                    del c.ACTIVE_GAMES[game_id]
                    print(f"Cleaned up game {game_id}")

            # Print stats every 30 seconds
            if int(time.time()) % 30 == 0:
                stats = c.ENGINE_POOL.get_stats() if c.ENGINE_POOL else {}
                print(
                    f"Pool stats: {stats.get('instance_count', 0)} instances, {len(c.ACTIVE_GAMES)} active games"
                )

            time.sleep(5)  # Check every 5 seconds

        except Exception as e:
            print(f"Instance handler error: {e}")
            traceback.print_exc()
            time.sleep(5)
