"""Configuration management for RRC web client."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path.home() / ".rrc-web"
DEFAULT_CONFIG_FILE = "config.json"
MAX_CONFIG_FILE_SIZE = 1024 * 1024


def get_default_config() -> dict[str, Any]:
    """Get default configuration values.

    Returns:
        Default configuration dictionary
    """
    return {
        "identity_path": str(DEFAULT_CONFIG_DIR / "identity"),
        "dest_name": "rrc.hub",
        "hub_hash": "",
        "nickname": "",
        "configdir": None,
        "server_port": 8080,
        "server_host": "localhost",
        "auto_join_room": "",
        "theme": "dark",
        "enable_auth": False,
        "auth_token": "",
        "enable_ssl": False,
        "ssl_cert_path": str(DEFAULT_CONFIG_DIR / "cert.pem"),
        "ssl_key_path": str(DEFAULT_CONFIG_DIR / "key.pem"),
        "session_timeout_minutes": 60,
        "allowed_origins": ["http://localhost:8080"],
        "enable_security_headers": True,
    }


def expand_path(path: str) -> str:
    """Expand ~ and environment variables in path.

    Args:
        path: Path string to expand

    Returns:
        Expanded absolute path
    """
    return str(Path(path).expanduser().resolve())


def get_config_path() -> str:
    """Get the configuration file path.

    Returns:
        Absolute path to config file
    """
    env_path = os.environ.get("RRC_WEB_CONFIG")
    if env_path:
        expanded = expand_path(env_path)
        return expanded

    return str(DEFAULT_CONFIG_DIR / DEFAULT_CONFIG_FILE)


def load_config() -> dict[str, Any]:
    """Load configuration from file.

    Returns:
        Configuration dictionary
    """
    config_path = Path(get_config_path())

    if not config_path.is_file():
        logger.info("Config file not found, creating default at %s", config_path)
        config = get_default_config()
        save_config(config)
        return config

    try:
        file_size = config_path.stat().st_size
        if file_size > MAX_CONFIG_FILE_SIZE:
            logger.error(
                "Config file too large: %d bytes (max %d)",
                file_size,
                MAX_CONFIG_FILE_SIZE,
            )
            return get_default_config()

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        logger.info("Loaded config from %s", config_path)

        default_config = get_default_config()
        for key, value in default_config.items():
            if key not in config:
                config[key] = value

        for key in ("identity_path", "configdir", "ssl_cert_path", "ssl_key_path"):
            if key in config and isinstance(config[key], str):
                config[key] = expand_path(config[key])

        return cast(dict[str, Any], config)
    except Exception as e:
        logger.exception("Failed to load config from %s: %s", config_path, e)
        return get_default_config()


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to file.

    Args:
        config: Configuration dictionary to save
    """
    config_path = Path(get_config_path())
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        logger.info("Saved config to %s", config_path)
    except Exception as e:
        logger.exception("Failed to save config to %s: %s", config_path, e)
