import configparser
import os
from pathlib import Path

CONFIG_FILE = "server.ini"


class ConfigError(RuntimeError):
    pass


def load_config():
    config = configparser.ConfigParser()
    if not config.read(CONFIG_FILE):
        raise ConfigError(f"Config file not found: {CONFIG_FILE}")
    return config


def resolve_path(base: Path, value: str) -> Path:
    """Resolve relative paths safely."""
    p = Path(value)
    return p if p.is_absolute() else (base / p).resolve()
