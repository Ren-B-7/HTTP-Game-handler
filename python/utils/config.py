"""
Configuration file loader and path resolver.

This module provides utilities for loading the server configuration from
an ini file and safely resolving file paths relative to the application
directory.

Functions:
    load_config: Load and parse the server.ini configuration file
    resolve_path: Safely resolve relative paths against a base directory

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

import configparser
from pathlib import Path

# Configuration file must be in the same directory as the base class
CONFIG_FILE = "server.ini"


class ConfigError(RuntimeError):
    """
    Raised when configuration file cannot be loaded or is invalid.

    This is a RuntimeError subclass to indicate that the application
    cannot proceed without valid configuration.

    Example:
        >>> if not config_file.exists():
        ...     raise ConfigError("server.ini not found")
    """


def load_config() -> configparser.ConfigParser:
    """
    Load and parse the server configuration file.

    This function attempts to read the server.ini file from the current
    directory. If the file doesn't exist or can't be read, it raises
    a ConfigError with a descriptive message.

    Returns:
        configparser.ConfigParser: Parsed configuration object with all sections

    Raises:
        ConfigError: If config file doesn't exist or can't be read

    Example:
        >>> config = load_config()
        >>> server_port = config['server'].getint('port', 5000)
        >>> session_timeout = config['session'].getint('timeout', 600)

    Note:
        The configuration file is expected to use standard INI format:
        ```ini
        [server]
        host = 0.0.0.0
        port = 5000

        [session]
        timeout = 600
        ```
    """
    config = configparser.ConfigParser()

    # read() returns a list of successfully read files
    # If the list is empty, the file wasn't found or couldn't be read
    if not config.read(CONFIG_FILE):
        raise ConfigError(f"Config file not found: {CONFIG_FILE}")

    return config


def resolve_path(base: Path, value: str) -> Path:
    """
    Resolve a path safely relative to a base directory.

    This function handles both absolute and relative paths correctly:
    - Absolute paths are returned as-is
    - Relative paths are resolved against the base directory
    - The result is always a fully resolved Path object

    Args:
        base: Base directory to resolve relative paths against
        value: Path string (can be absolute or relative)

    Returns:
        Path: Fully resolved Path object

    Example:
        >>> script_dir = Path(__file__).parent
        >>>
        >>> # Relative path
        >>> html_dir = resolve_path(script_dir, "frontend/html")
        >>> # Returns: /path/to/script/frontend/html
        >>>
        >>> # Absolute path (returned as-is)
        >>> logs = resolve_path(script_dir, "/var/log/chess")
        >>> # Returns: /var/log/chess

    Note:
        Using resolve() ensures that symbolic links are followed and
        the path is normalized (e.g., "../dir" becomes the actual parent).
    """
    p = Path(value)

    # Absolute paths are returned unchanged
    if p.is_absolute():
        return p

    # Relative paths are joined with base and fully resolved
    return (base / p).resolve()
