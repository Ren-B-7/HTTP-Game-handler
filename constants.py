"""
Constants and configuration for the Chess server.

This module contains all configuration values, paths, and global state objects
used throughout the server application.
"""

import sys
import sqlite3
import threading
import queue
from pathlib import Path
from typing import Optional

from SessionManager import SessionManager
from ServerState import ServerState
from config import load_config, resolve_path
from EngineHandler import EnginePool

# Load configuration once
config = load_config()

# Cache config sections for faster access
_server_cfg = config["server"]
_frontend_cfg = config["frontend"]
_icons_cfg = config["icons"]
_handler_cfg = config["handler"]
_database_cfg = config["database"]
_session_cfg = config["session"]

# Directory setup - ensure we're in the script directory
SCRIPT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = resolve_path(SCRIPT_DIR, _frontend_cfg["directory"])
ICON_DIR = resolve_path(SCRIPT_DIR, _icons_cfg["directory"])

# Server configuration
SERVER_HOST = _server_cfg["host"]
SERVER_PORT = _server_cfg.getint("port")
SERVER_TIMEOUT = _server_cfg.getint("timeout")

# Game executables
BOT_CLI = ""

HANDLER_DIR = resolve_path(SCRIPT_DIR, _handler_cfg["directory"])
HANDLER_BIN = HANDLER_DIR / _handler_cfg["filename"]
HANDLER_ARGS = _handler_cfg.get("args", "")

if not HANDLER_BIN.is_file():
    raise FileNotFoundError(f"Game executable not found: {HANDLER_BIN}")

GAME_HANDLER = f"{HANDLER_BIN} {HANDLER_ARGS}"

# Database configuration
ACTIVE_DB = _database_cfg["main"]
SESSION_DB = resolve_path(SCRIPT_DIR, _database_cfg["sessions"])

# Global state (thread-safe singleton)
SERVER_STATE = ServerState()

# Server components
PROMISCUOUS_IPS = set()

# Session configuration
SESSION_TIMEOUT = _session_cfg.getint("timeout")
SESSION_CACHE_SIZE = _session_cfg.getint("max_cache_size")

if not (SESSION_TIMEOUT and SESSION_CACHE_SIZE and SESSION_DB):
    print("Missing config items relating to session")
    sys.exit(1)

SESSION_MANAGER = SessionManager(
    SESSION_DB,
    session_timeout=SESSION_TIMEOUT,
    max_cache_size=SESSION_CACHE_SIZE,
)

# Game state
ACTIVE_GAMES = {}
MATCHMAKING_QUEUE = queue.Queue()

# Database connection variables
DB_CONNECTION: Optional[sqlite3.Connection] = None
DB_CURSOR: Optional[sqlite3.Cursor] = None
DB_LOCK = threading.Lock()

HTTPD = None

ENGINE_POOL: Optional[EnginePool] = None

# HTML file paths
LOGIN_HTML = FRONTEND_DIR / _frontend_cfg["login"]
REGISTER_HTML = FRONTEND_DIR / _frontend_cfg["register"]
GAME_HTML = FRONTEND_DIR / _frontend_cfg["game"]
STATS_HTML = FRONTEND_DIR / _frontend_cfg["stats"]
HOME_HTML = FRONTEND_DIR / _frontend_cfg["home"]
PROFILE_HTML = FRONTEND_DIR / _frontend_cfg["profile"]

for path in (LOGIN_HTML, REGISTER_HTML):
    if not path.is_file():
        print(f"WARNING: Missing file: {path}")

# Icon configuration
# This is for the Favicon icons, since the browser requests them bare and if its
# not in the root directory it would fail (I prefer icons to be separate)
ICONS_DIRECTORY = resolve_path(SCRIPT_DIR, _icons_cfg["directory"])

# Optimized icon file set creation (split once, strip once)
ICON_FILES = frozenset(
    "/" + name for name in (n.strip() for n in _icons_cfg["files"].split(",")) if name
)
