"""Utility functions for RRC web client."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import RNS

logger = logging.getLogger(__name__)


def get_timestamp() -> str:
    """Get current timestamp as HH:MM:SS string.

    Returns:
        Formatted timestamp string
    """
    return datetime.now().strftime("%H:%M:%S")


def expand_path(p: str) -> str:
    """Expand ~ and environment variables in path.

    Args:
        p: Path string to expand

    Returns:
        Expanded absolute path
    """
    return str(Path(p).expanduser().resolve())


def load_or_create_identity(path: str) -> RNS.Identity:
    """Load identity from file or create a new one.

    Args:
        path: Path to identity file

    Returns:
        RNS.Identity instance
    """
    identity_path = Path(expand_path(path))
    identity_path.parent.mkdir(parents=True, exist_ok=True)

    if identity_path.is_file():
        logger.info("Loading identity from %s", identity_path)
        try:
            import stat

            identity_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except Exception as e:
            logger.warning("Could not set secure permissions on identity file: %s", e)
        return RNS.Identity.from_file(str(identity_path))
    else:
        logger.info("Creating new identity at %s", identity_path)
        identity = RNS.Identity()
        identity.to_file(str(identity_path))
        try:
            import stat

            identity_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except Exception as e:
            logger.warning("Could not set secure permissions on identity file: %s", e)
        return identity


def normalize_room_name(room: str) -> str | None:
    """Normalize a room name to lowercase and stripped.

    Args:
        room: Room name to normalize

    Returns:
        Normalized room name, or None if invalid
    """
    if not isinstance(room, str):
        return None

    normalized = room.strip().lower()
    if not normalized:
        return None

    return normalized


def sanitize_text_input(text: str, max_length: int = 1024) -> str | None:
    """Sanitize text input for sending.

    Note: This is a basic length check. The actual message size limit
    is determined by the link MDU (Maximum Data Unit), which is checked
    in the Client._send() method before transmission.

    Args:
        text: Text to sanitize
        max_length: Maximum allowed length (conservative estimate)

    Returns:
        Sanitized text, or None if invalid
    """
    if not isinstance(text, str):
        return None

    sanitized = text.strip()
    if not sanitized:
        return None

    if len(sanitized) > max_length:
        return None

    for char in sanitized:
        code = ord(char)
        if code < 32 and code not in (9, 10, 13):
            return None
        if code == 0 or code == 0xFFFE or code == 0xFFFF:
            return None

    return sanitized


def sanitize_display_name(name: str, max_length: int = 64) -> str | None:
    """Sanitize display names like hub names and nicknames.

    Removes control characters and limits length. More permissive than
    sanitize_text_input as these are display-only and don't allow newlines.

    Args:
        name: Name to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized name, or None if invalid
    """
    if not isinstance(name, str):
        return None

    sanitized = name.strip()
    if not sanitized:
        return None

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    cleaned = ""
    for char in sanitized:
        code = ord(char)
        if code < 32 or code == 0x7F or code == 0xFFFE or code == 0xFFFF:
            continue
        cleaned += char

    if not cleaned:
        return None

    return cleaned


def parse_hash(text: str) -> bytes:
    """Parse a hexadecimal hash string to bytes.

    Args:
        text: Hex string to parse

    Returns:
        Parsed bytes

    Raises:
        ValueError: If hash string is invalid
    """
    text = text.strip().replace(":", "").replace(" ", "")

    try:
        return bytes.fromhex(text)
    except ValueError as e:
        raise ValueError(f"Invalid hash format: {e}") from e
