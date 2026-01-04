"""RRC envelope creation and validation."""

from __future__ import annotations

import os
import time
from typing import Any

from .constants import (
    K_BODY,
    K_ID,
    K_NICK,
    K_ROOM,
    K_SRC,
    K_T,
    K_TS,
    K_V,
    RRC_VERSION,
)


def now_ms() -> int:
    """Get current time in milliseconds.

    Returns:
        Current time as milliseconds since epoch
    """
    return int(time.time() * 1000)


def msg_id() -> bytes:
    """Generate a random 8-byte message ID.

    Returns:
        Random 8 bytes
    """
    return os.urandom(8)


def make_envelope(
    msg_type: int,
    *,
    src: bytes,
    room: str | None = None,
    body: Any = None,
    nick: str | None = None,
    mid: bytes | None = None,
    ts: int | None = None,
) -> dict:
    """Create an RRC protocol envelope.

    Args:
        msg_type: RRC message type constant (T_*)
        src: Sender identity hash (bytes)
        room: Optional room name
        body: Optional message body
        nick: Optional nickname
        mid: Optional message ID (generated if not provided)
        ts: Optional timestamp in milliseconds (current time if not provided)

    Returns:
        RRC envelope dictionary with integer keys
    """
    env: dict[int, Any] = {
        K_V: RRC_VERSION,
        K_T: int(msg_type),
        K_ID: mid or msg_id(),
        K_TS: ts or now_ms(),
        K_SRC: src,
    }

    if room is not None:
        env[K_ROOM] = room
    if body is not None:
        env[K_BODY] = body
    if nick is not None:
        env[K_NICK] = nick

    return env


def validate_envelope(env: dict) -> None:
    """Validate an RRC envelope structure.

    Args:
        env: Envelope dictionary to validate

    Raises:
        TypeError: If envelope structure is invalid
        ValueError: If envelope values are invalid
    """
    if not isinstance(env, dict):
        raise TypeError("envelope must be a dict")

    for k in env:
        if not isinstance(k, int):
            raise TypeError("envelope keys must be integers")
        if k < 0:
            raise ValueError("envelope keys must be unsigned integers")

    for k in (K_V, K_T, K_ID, K_TS, K_SRC):
        if k not in env:
            raise ValueError(f"missing required envelope key {k}")

    v = env[K_V]
    if not isinstance(v, int):
        raise TypeError("protocol version must be an integer")
    if v != RRC_VERSION:
        raise ValueError(f"unsupported protocol version {v}")

    t = env[K_T]
    if not isinstance(t, int):
        raise TypeError("message type must be an integer")
    if t < 0:
        raise ValueError("message type must be unsigned")

    mid = env[K_ID]
    if not isinstance(mid, (bytes, bytearray)):
        raise TypeError("message ID must be bytes")
    if len(mid) != 8:
        raise ValueError("message ID must be exactly 8 bytes")

    ts = env[K_TS]
    if not isinstance(ts, int):
        raise TypeError("timestamp must be an integer")
    if ts < 0:
        raise ValueError("timestamp must be unsigned")

    src = env[K_SRC]
    if not isinstance(src, (bytes, bytearray)):
        raise TypeError("source identity must be bytes")
    if len(src) not in (16, 32):
        raise ValueError(f"source identity hash has unexpected length: {len(src)} bytes")

    if K_ROOM in env:
        room = env[K_ROOM]
        if not isinstance(room, str):
            raise TypeError("room name must be a string")
        if len(room) == 0:
            raise ValueError("room name cannot be empty")
        if len(room) > 64:
            raise ValueError("room name too long (max 64 characters)")

    if K_NICK in env:
        nick = env[K_NICK]
        if not isinstance(nick, str):
            raise TypeError("nickname must be a string")
        if len(nick) == 0:
            raise ValueError("nickname cannot be empty")
        if len(nick) > 32:
            raise ValueError("nickname too long (max 32 characters)")

    if K_BODY in env:
        body = env[K_BODY]
        if body is not None and not isinstance(
            body, (str, int, float, bool, dict, list, bytes, bytearray)
        ):
            raise TypeError(f"body has unsupported type: {type(body).__name__}")
