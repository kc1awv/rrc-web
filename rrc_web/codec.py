"""CBOR codec for RRC messages."""

from __future__ import annotations

from typing import Any, cast

import cbor2

MAX_CBOR_SIZE = 1024 * 512


def encode(obj: dict) -> bytes:
    """Encode a Python object to CBOR bytes.

    Args:
        obj: Python dictionary to encode

    Returns:
        CBOR encoded bytes
    """
    return cbor2.dumps(obj)


def decode(data: bytes) -> dict:
    """Decode CBOR bytes to a Python object.

    Args:
        data: CBOR encoded bytes

    Returns:
        Decoded Python dictionary

    Raises:
        ValueError: If data exceeds size limit
    """
    if len(data) > MAX_CBOR_SIZE:
        raise ValueError(f"CBOR data too large: {len(data)} bytes (max {MAX_CBOR_SIZE})")
    return cast(dict[Any, Any], cbor2.loads(data))
