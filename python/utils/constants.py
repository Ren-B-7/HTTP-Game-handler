"""
Constants and configuration for the Chess server.

Global Components:
    - SERVER_STATE: Thread-safe server state manager
    - SESSION_MANAGER: SQLite-backed session manager
    - COMPRESSION_CACHE: Cached gzip compression for static files
    - ENGINE_POOL: Pool of game engine instances (initialized later)

Configuration Sections:
    - Server: Host, port, timeout settings
    - SSL: Certificate and encryption settings
    - Frontend: HTML file paths
    - Icons: Favicon configuration
    - Handler: Game engine configuration
    - Database: Database file paths
    - Session: Session management settings

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

import sys
import sqlite3
import threading
import queue
from pathlib import Path
from typing import Optional

from .SessionManager import SessionManager
from .ServerState import ServerState
from .config import load_config, resolve_path
from .EngineHandler import EnginePool
from .CompressionPool import SimpleCachedCompressor

config = load_config()

_server_cfg = config["server"]
_ssl_cfg = config["ssl"]
_frontend_cfg = config["frontend"]
_icons_cfg = config["icons"]
_handler_cfg = config["handler"]
_database_cfg = config["database"]
_session_cfg = config["session"]

SCRIPT_DIR = Path(__file__).resolve().parent.parent

FRONTEND_DIR = resolve_path(SCRIPT_DIR, _frontend_cfg["directory"])

ICON_DIR = resolve_path(SCRIPT_DIR, _icons_cfg["directory"])

SERVER_HOST = _server_cfg["host"]
SERVER_PORT = _server_cfg.getint("port", 5000)
SERVER_TIMEOUT = _server_cfg.getint("timeout", fallback=300)


# SSL certificate and key paths (None if SSL disabled)
CERT_FILE = None
KEY_FILE = None

if _ssl_cfg.getboolean("enable"):
    CERT_FILE = _ssl_cfg.get("cert", None)
    KEY_FILE = _ssl_cfg.get("key", None)

HANDLER_DIR = resolve_path(SCRIPT_DIR, _handler_cfg["directory"])
HANDLER_BIN = HANDLER_DIR / _handler_cfg["filename"]
HANDLER_ARGS = _handler_cfg.get("args", "")

# Verify game executable exists before proceeding
if not HANDLER_BIN.is_file():
    raise FileNotFoundError(f"Game executable not found: {HANDLER_BIN}")

GAME_HANDLER = f"{HANDLER_BIN} {HANDLER_ARGS}"

# Main database file (users, games, stats)
ACTIVE_DB = _database_cfg["main"]

# Session database file (separate for easier cleanup and management)
SESSION_DB = resolve_path(SCRIPT_DIR, _database_cfg["sessions"])

SERVER_STATE = ServerState()

# Session timeout in seconds (how long before inactive sessions expire)
SESSION_TIMEOUT = _session_cfg.getint("timeout")

# Maximum number of sessions to cache in memory (LRU eviction)
SESSION_CACHE_SIZE = _session_cfg.getint("max_cache_size")

# Validate critical session configuration
if not (SESSION_TIMEOUT and SESSION_CACHE_SIZE and SESSION_DB):
    print("Missing config items relating to session")
    sys.exit(1)

SESSION_MANAGER = SessionManager(
    SESSION_DB,
    session_timeout=SESSION_TIMEOUT,
    max_cache_size=SESSION_CACHE_SIZE,
)

# Cached gzip compressor for static files
# Avoids re-compressing the same files on every request
COMPRESSION_CACHE = SimpleCachedCompressor(
    max_cache_size=_handler_cfg.getint("max_file_cache", 128)
)

# Maximum POST request size in KB (prevents memory exhaustion attacks)
MAX_POST_SIZE = _handler_cfg.getint("max_post_request_kb", 64) * 1000

# Active games dictionary: {game_id: game_state}
ACTIVE_GAMES = {}

# Queue for matchmaking requests (FIFO)
MATCHMAKING_QUEUE = queue.Queue()

# Track players waiting for matchmaking results
# Format: {session_id: {"game_id": str, "notified": bool}}
# This ensures players can poll for their game_id after matchmaking
MATCHMAKING_RESULTS = {}

# Global database connection and cursor (protected by DB_LOCK)
# These are initialized later by the main application
DB_CONNECTION: Optional[sqlite3.Connection] = None
DB_CURSOR: Optional[sqlite3.Cursor] = None
DB_LOCK = threading.Lock()  # Ensures thread-safe database access

# Global reference to HTTP server instance (set by main application)
HTTPD = None

# Pool of game engine instances (initialized by main application)
# Handles load balancing and auto-scaling of engine processes
ENGINE_POOL: Optional[EnginePool] = None

# Frontend HTML files
LOGIN_HTML = FRONTEND_DIR / _frontend_cfg["login"]
REGISTER_HTML = FRONTEND_DIR / _frontend_cfg["register"]
GAME_HTML = FRONTEND_DIR / _frontend_cfg["game"]
STATS_HTML = FRONTEND_DIR / _frontend_cfg["stats"]
HOME_HTML = FRONTEND_DIR / _frontend_cfg["home"]
PROFILE_HTML = FRONTEND_DIR / _frontend_cfg["profile"]

# Warn about missing critical files (don't fail - allows partial functionality)
for path in (LOGIN_HTML, REGISTER_HTML):
    if not path.is_file():
        print(f"WARNING: Missing file: {path}")

# Directory containing favicon files
# These are typically in /icons but accessed as /favicon.ico, /apple-touch-icon.png, etc.
ICONS_DIRECTORY = resolve_path(SCRIPT_DIR, _icons_cfg["directory"])

ICON_FILES = frozenset(
    "/" + name for name in (n.strip() for n in _icons_cfg["files"].split(",")) if name
)
