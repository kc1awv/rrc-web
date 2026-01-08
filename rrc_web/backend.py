"""Backend service that coordinates RRC client and WebSocket server."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import cbor2
import RNS

from .client import Client, ClientConfig
from .config import load_config, save_config
from .constants import B_JOINED_USERS, B_WELCOME_HUB, K_BODY, K_ID, K_NICK, K_ROOM, K_SRC, K_TS
from .utils import load_or_create_identity, parse_hash

logger = logging.getLogger(__name__)

STALE_HUB_THRESHOLD_SECONDS = 3600
MAX_MESSAGES_PER_ROOM = 1000
MAX_TOTAL_RESOURCES = 100
MAX_ROOMS = 100
REQUIRED_HUB_HASH_LENGTH = 32
MAX_ANNOUNCE_DATA_SIZE = 10240
STATE_MESSAGES_TO_RETURN = 100
MAX_TIMESTAMP_SKEW_SECONDS = 300


class HubAnnounceHandler:
    """Handler for RRC hub announcements on the Reticulum network."""

    def __init__(self, backend_service):
        """Initialize the announce handler.

        Args:
            backend_service: Reference to the BackendService instance
        """
        self.backend_service = backend_service
        self.aspect_filter = "rrc.hub"

    def received_announce(
        self,
        destination_hash: bytes,
        announced_identity: RNS.Identity,  # noqa: ARG002
        app_data: bytes,
    ) -> None:
        """Handle received announces from the network.

        Args:
            destination_hash: Hash of the announcing destination
            announced_identity: Identity that made the announcement (unused)
            app_data: Application data from the announcement
        """
        try:
            hash_hex = destination_hash.hex()

            hub_name = None
            aspect = self.aspect_filter

            if app_data:
                logger.debug(f"Received app_data size: {len(app_data)} bytes")

                if len(app_data) > MAX_ANNOUNCE_DATA_SIZE:
                    logger.warning(
                        f"Ignoring announce with oversized app_data: {len(app_data)} bytes "
                        f"(max {MAX_ANNOUNCE_DATA_SIZE})"
                    )
                    return

                try:
                    decoded = cbor2.loads(app_data)
                    logger.debug(f"CBOR decoded app_data type: {type(decoded).__name__}")

                    if isinstance(decoded, dict):
                        if len(decoded) > 20:
                            logger.warning(
                                f"Ignoring announce with oversized dict: {len(decoded)} keys"
                            )
                            return
                        for key, value in decoded.items():
                            if not isinstance(key, (str, int, bytes)):
                                logger.warning(f"Invalid dict key type in announce: {type(key)}")
                                return
                            if isinstance(value, (dict, list)) and len(str(value)) > 1000:
                                logger.warning("Oversized nested structure in announce")
                                return

                        if decoded.get("proto") == "rrc" and "hub" in decoded:
                            hub_name = decoded["hub"] if isinstance(decoded["hub"], str) else None
                            logger.debug(f"Found RRC hub: {hub_name}")
                        else:
                            hub_name = (
                                decoded.get("name")
                                if isinstance(decoded.get("name"), str)
                                else (
                                    decoded.get("n")
                                    if isinstance(decoded.get("n"), str)
                                    else (
                                        decoded.get("hub")
                                        if isinstance(decoded.get("hub"), str)
                                        else None
                                    )
                                )
                            )
                    elif isinstance(decoded, list):
                        if len(decoded) > 20:
                            logger.warning(
                                f"Ignoring announce with oversized list: {len(decoded)} items"
                            )
                            return
                        if len(decoded) >= 1 and isinstance(decoded[-1], str):
                            hub_name = decoded[-1]
                    elif isinstance(decoded, str):
                        if len(decoded) > 200:
                            logger.warning(
                                f"Ignoring announce with oversized string: {len(decoded)} chars"
                            )
                            return
                        hub_name = decoded
                except Exception as cbor_err:
                    logger.debug(f"CBOR decode failed: {cbor_err}")

                    try:
                        app_data_str = app_data.decode("utf-8")
                        logger.debug(f"UTF-8 decoded app_data length: {len(app_data_str)}")
                        hub_name = app_data_str
                    except Exception as utf8_err:
                        logger.debug(f"UTF-8 decode failed: {utf8_err}")
                        logger.debug(f"Could not decode app_data, size: {len(app_data)} bytes")
                        return

            if not hub_name:
                hub_name = f"Hub {hash_hex[:8]}"
                logger.debug("No hub name found, using default")

            from .utils import sanitize_display_name

            sanitized_hub_name = sanitize_display_name(hub_name, max_length=200)
            if not sanitized_hub_name:
                sanitized_hub_name = f"Hub {hash_hex[:8]}"
                logger.debug("Hub name sanitization failed, using default")

            logger.debug(f"Parsed hub announcement from {hash_hex[:16]}...")

            with self.backend_service._lock:
                self.backend_service.discovered_hubs[hash_hex] = {
                    "hash": hash_hex,
                    "name": sanitized_hub_name,
                    "aspect": aspect,
                    "last_seen": time.time(),
                }
            logger.info(f"Discovered RRC hub: {sanitized_hub_name} ({hash_hex[:16]}...)")

            self.backend_service.save_discovered_hubs()

            if self.backend_service.loop and self.backend_service.broadcast:
                asyncio.run_coroutine_threadsafe(
                    self.backend_service.broadcast(
                        {
                            "type": "hub_discovered",
                            "hub": self.backend_service.discovered_hubs[hash_hex],
                        }
                    ),
                    self.backend_service.loop,
                )
        except (ValueError, TypeError) as e:
            logger.warning("Invalid announcement data: %s", e)
        except Exception as e:
            logger.exception("Unexpected error processing announcement: %s", e)


class BackendService:
    """Backend service coordinating RRC client and WebSocket communications.

    Thread-Safety:
        This class is designed to handle multi-threaded access safely.

        - init_reticulum() MUST be called from the main thread before start()
        - All async methods (_handle_*) run on the asyncio event loop
        - Callbacks from the RRC client run on RNS worker threads and use
          asyncio.run_coroutine_threadsafe to safely dispatch to the event loop
        - Internal state (rooms, nicknames, discovered_hubs) is protected by self._lock
        - The broadcast callback is thread-safe when invoked via run_coroutine_threadsafe

        Important: Do not call blocking RNS operations directly from async methods.
        Use run_in_executor to avoid blocking the event loop.
    """

    def __init__(self):
        """Initialize the backend service."""
        self.config = load_config()
        self.client: Client | None = None
        self.identity: RNS.Identity | None = None
        self.reticulum: RNS.Reticulum | None = None
        self.active_room: str = "[Hub]"
        self.rooms: dict[str, dict] = {"[Hub]": {"messages": [], "users": set()}}
        self.nicknames: dict[str, str] = {}
        self.hub_name: str | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.broadcast: Callable[[dict], Awaitable[None]] | None = None
        self.discovered_hubs: dict[str, dict] = {}
        self.announce_handler: HubAnnounceHandler | None = None

        self.ping_task: asyncio.Task | None = None
        self.last_ping_time: float | None = None
        self.latency_ms: int | None = None

        self.room_operation_times: dict[str, list[float]] = {}
        self.room_op_rate_limit = 10
        self.room_op_rate_window = 5.0

        self.max_messages_per_room: int = MAX_MESSAGES_PER_ROOM
        self.max_total_resources: int = MAX_TOTAL_RESOURCES
        self.max_rooms: int = MAX_ROOMS
        self.required_hub_hash_length: int = REQUIRED_HUB_HASH_LENGTH

        config_dir_str = self.config.get("configdir") or "~/.rrc-web"
        config_dir = Path(config_dir_str).expanduser()
        self.hub_cache_path = config_dir / "discovered_hubs.json"
        self._lock = threading.RLock()

        self.load_discovered_hubs()

    def init_reticulum(self) -> None:
        """Initialize Reticulum (must be called from main thread)."""
        try:
            configdir = self.config.get("configdir")
            if RNS.Reticulum.get_instance() is None:
                self.reticulum = RNS.Reticulum(configdir=configdir)
                logger.info("Reticulum initialized")
            else:
                self.reticulum = RNS.Reticulum.get_instance()
                logger.info("Using existing Reticulum instance")

            self.announce_handler = HubAnnounceHandler(self)
            RNS.Transport.register_announce_handler(self.announce_handler)
            logger.info("Hub discovery announce handler registered")

            self.cleanup_stale_hubs()
        except Exception as e:
            logger.error("Failed to initialize Reticulum: %s", e)
            raise

    async def start(self) -> None:
        """Start the backend service."""
        self.loop = asyncio.get_event_loop()
        logger.info("Backend service started")

    async def stop(self) -> None:
        """Stop the backend service."""
        if self.client:
            await asyncio.get_event_loop().run_in_executor(None, self.client.close)

        logger.info("Backend service stopped")

    async def handle_ws_message(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle incoming WebSocket message from browser.

        Args:
            data: Message data from browser

        Returns:
            Response data or None
        """
        msg_type = data.get("type")

        if msg_type == "connect":
            return await self._handle_connect(data)
        elif msg_type == "disconnect":
            return await self._handle_disconnect()
        elif msg_type == "join_room":
            return await self._handle_join_room(data)
        elif msg_type == "part_room":
            return await self._handle_part_room(data)
        elif msg_type == "send_message":
            return await self._handle_send_message(data)
        elif msg_type == "send_command":
            return await self._handle_send_command(data)
        elif msg_type == "set_nickname":
            return await self._handle_set_nickname(data)
        elif msg_type == "set_active_room":
            return await self._handle_set_active_room(data)
        elif msg_type == "get_state":
            return await self._handle_get_state()
        elif msg_type == "get_discovered_hubs":
            return await self._handle_get_discovered_hubs()
        else:
            logger.warning("Unknown message type: %s", msg_type)
            return {"type": "error", "error": f"Unknown message type: {msg_type}"}

    async def _handle_connect(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle connect request from browser.

        Args:
            data: Connection parameters

        Returns:
            Response data
        """
        try:
            identity_path = data.get("identity_path", self.config["identity_path"])
            if not isinstance(identity_path, str) or len(identity_path) > 1024:
                return {"type": "error", "error": "Invalid identity_path parameter"}

            dest_name = data.get("dest_name", self.config["dest_name"])
            if not isinstance(dest_name, str) or len(dest_name) > 256:
                return {"type": "error", "error": "Invalid dest_name parameter"}

            hub_hash = data.get("hub_hash", self.config["hub_hash"])
            if not isinstance(hub_hash, str) or len(hub_hash) > 128:
                return {"type": "error", "error": "Invalid hub_hash parameter"}

            nickname = data.get("nickname", self.config["nickname"])
            if nickname and (not isinstance(nickname, str) or len(nickname) > 32):
                return {"type": "error", "error": "Invalid nickname parameter"}

            self.config.update(
                {
                    "identity_path": identity_path,
                    "dest_name": dest_name,
                    "hub_hash": hub_hash,
                    "nickname": nickname,
                }
            )
            save_config(self.config)

            self.identity = await asyncio.get_event_loop().run_in_executor(
                None, load_or_create_identity, identity_path
            )

            client_config = ClientConfig(dest_name=dest_name)
            self.client = Client(
                self.identity,
                client_config,
                nickname=nickname if nickname else None,
            )

            self.client.on_message = lambda env: asyncio.run_coroutine_threadsafe(  # type: ignore[assignment]
                self._on_message(env), self.loop  # type: ignore[arg-type]
            )
            self.client.on_notice = lambda env: asyncio.run_coroutine_threadsafe(  # type: ignore[assignment]
                self._on_notice(env), self.loop  # type: ignore[arg-type]
            )
            self.client.on_error = lambda env: asyncio.run_coroutine_threadsafe(  # type: ignore[assignment]
                self._on_error(env), self.loop  # type: ignore[arg-type]
            )
            self.client.on_welcome = lambda env: asyncio.run_coroutine_threadsafe(  # type: ignore[assignment]
                self._on_welcome(env), self.loop  # type: ignore[arg-type]
            )
            self.client.on_joined = lambda room, env: asyncio.run_coroutine_threadsafe(  # type: ignore[assignment]
                self._on_joined(room, env), self.loop  # type: ignore[arg-type]
            )
            self.client.on_parted = lambda room, env: asyncio.run_coroutine_threadsafe(  # type: ignore[assignment]
                self._on_parted(room, env), self.loop  # type: ignore[arg-type]
            )
            self.client.on_close = lambda: asyncio.run_coroutine_threadsafe(  # type: ignore[assignment]
                self._on_close(), self.loop  # type: ignore[arg-type]
            )
            self.client.on_pong = lambda env: asyncio.run_coroutine_threadsafe(  # type: ignore[assignment]
                self._on_pong(env), self.loop  # type: ignore[arg-type]
            )

            if not hub_hash or not isinstance(hub_hash, str):
                return {
                    "type": "error",
                    "error": "Invalid hub hash: must be a non-empty string",
                }

            hub_hash_clean = hub_hash.strip().replace(":", "").replace(" ", "").lower()

            if not all(c in "0123456789abcdef" for c in hub_hash_clean):
                return {
                    "type": "error",
                    "error": "Hub hash must contain only hexadecimal characters",
                }

            if len(hub_hash_clean) != self.required_hub_hash_length:
                return {
                    "type": "error",
                    "error": f"Hub hash must be exactly {self.required_hub_hash_length} hexadecimal characters (got {len(hub_hash_clean)})",
                }

            hub_hash_bytes = await asyncio.get_event_loop().run_in_executor(
                None, parse_hash, hub_hash
            )

            await asyncio.get_event_loop().run_in_executor(
                None, self.client.connect, hub_hash_bytes
            )

            auto_join = self.config.get("auto_join_room")
            if auto_join and self.client:
                await asyncio.get_event_loop().run_in_executor(None, self.client.join, auto_join)

            return {
                "type": "connected",
                "identity_hash": self.identity.hash.hex() if self.identity else "",
                "nickname": nickname,
            }

        except TimeoutError as e:
            logger.error("Connection timeout: %s", e)
            return {
                "type": "error",
                "error": f"Connection timeout: {e}. Ensure the hub is online and reachable on the Reticulum network.",
            }
        except ValueError as e:
            logger.error("Connection validation error: %s", e)
            return {
                "type": "error",
                "error": f"Invalid connection parameters: {e}",
            }
        except OSError as e:
            logger.error("Network or I/O error during connection: %s", e)
            return {
                "type": "error",
                "error": f"Network error: {e}. Check your network connectivity.",
            }
        except Exception as e:
            logger.exception("Unexpected error during connection: %s", e)
            return {
                "type": "error",
                "error": f"Connection failed: {e}. Check your Reticulum configuration and network connectivity.",
            }

    async def _handle_disconnect(self) -> dict[str, Any]:
        """Handle disconnect request from browser.

        Returns:
            Response data
        """
        try:
            if self.client:
                await asyncio.get_event_loop().run_in_executor(None, self.client.close)
                self.client = None

            self.rooms = {"[Hub]": {"messages": [], "users": set()}}
            self.active_room = "[Hub]"
            self.hub_name = None

            return {"type": "disconnected"}
        except OSError as e:
            logger.error("I/O error during disconnect: %s", e)
            return {"type": "error", "error": f"Disconnect error: {e}"}
        except Exception as e:
            logger.exception("Unexpected error during disconnect: %s", e)
            return {"type": "error", "error": str(e)}

    async def _handle_join_room(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle join room request from browser.

        Args:
            data: Room join parameters

        Returns:
            Response data
        """
        try:
            room = data.get("room")
            if not isinstance(room, str) or len(room) > 64:
                return {"type": "error", "error": "Invalid room name"}

            if not self.client:
                return {"type": "error", "error": "Not connected to hub"}

            from .utils import normalize_room_name

            normalized_room = normalize_room_name(room)
            if not normalized_room:
                return {"type": "error", "error": "Invalid room name"}

            if not self._check_room_operation_rate_limit(f"join:{normalized_room}"):
                return {
                    "type": "error",
                    "error": "Too many join requests. Please wait a moment.",
                }

            await asyncio.get_event_loop().run_in_executor(None, self.client.join, normalized_room)

            return {"type": "join_requested", "room": room}
        except ValueError as e:
            logger.error("Invalid room name for join: %s", e)
            return {"type": "error", "error": f"Invalid room name: {e}"}
        except Exception as e:
            logger.exception("Unexpected error joining room: %s", e)
            return {"type": "error", "error": str(e)}

    async def _handle_part_room(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle part room request from browser.

        Args:
            data: Room part parameters

        Returns:
            Response data
        """
        try:
            room = data.get("room")
            if not isinstance(room, str) or len(room) > 64:
                return {"type": "error", "error": "Invalid room name"}

            if not self.client:
                return {"type": "error", "error": "Not connected to hub"}

            from .utils import normalize_room_name

            normalized_room = normalize_room_name(room)
            if not normalized_room:
                return {"type": "error", "error": "Invalid room name"}

            if not self._check_room_operation_rate_limit(f"part:{normalized_room}"):
                return {
                    "type": "error",
                    "error": "Too many part requests. Please wait a moment.",
                }

            await asyncio.get_event_loop().run_in_executor(None, self.client.part, normalized_room)

            return {"type": "part_requested", "room": room}
        except ValueError as e:
            logger.error("Invalid room name for part: %s", e)
            return {"type": "error", "error": f"Invalid room name: {e}"}
        except Exception as e:
            logger.exception("Unexpected error leaving room: %s", e)
            return {"type": "error", "error": str(e)}

    async def _handle_send_message(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle send message request from browser.

        Args:
            data: Message parameters

        Returns:
            Response data
        """
        try:
            room = data.get("room")
            text = data.get("text")

            if not isinstance(room, str) or len(room) > 64:
                return {"type": "error", "error": "Invalid room name"}

            if not isinstance(text, str) or len(text) > 10000:
                return {"type": "error", "error": "Invalid message text"}

            if not self.client:
                return {"type": "error", "error": "Not connected to hub"}

            from .utils import normalize_room_name, sanitize_text_input

            normalized_room = normalize_room_name(room)
            if not normalized_room:
                return {"type": "error", "error": "Invalid room name"}

            sanitized_text = sanitize_text_input(text)
            if not sanitized_text:
                return {"type": "error", "error": "Invalid message text"}

            if sanitized_text.startswith("/"):
                return await self._handle_command(normalized_room, sanitized_text)

            msg_id = await asyncio.get_event_loop().run_in_executor(
                None, self.client.msg, normalized_room, sanitized_text
            )

            return {"type": "message_sent", "message_id": msg_id.hex()}
        except ValueError as e:
            logger.error("Invalid message data: %s", e)
            return {"type": "error", "error": f"Invalid message: {e}"}
        except Exception as e:
            logger.exception("Unexpected error sending message: %s", e)
            return {"type": "error", "error": str(e)}

    async def _handle_command(self, room: str, text: str) -> dict[str, Any]:
        """Handle slash command.

        Args:
            room: Current room
            text: Command text

        Returns:
            Response data
        """
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()

        if cmd == "/join" and len(parts) > 1:
            return await self._handle_join_room({"room": parts[1]})
        elif cmd == "/part":
            target_room = parts[1] if len(parts) > 1 else room
            return await self._handle_part_room({"room": target_room})
        elif cmd == "/ping":
            if self.client:
                await asyncio.get_event_loop().run_in_executor(None, self.client.ping)
            return {"type": "command_executed", "command": "ping"}
        else:
            if self.client:
                await asyncio.get_event_loop().run_in_executor(None, self.client.msg, room, text)
            return {"type": "message_sent"}

    async def _handle_set_active_room(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle set active room request from browser.

        Args:
            data: Room parameters

        Returns:
            Response data
        """
        room = data.get("room")
        if not isinstance(room, str) or len(room) > 64:
            return {"type": "error", "error": "Invalid room name"}

        if room:
            self.active_room = room
            return {"type": "active_room_changed", "room": room}
        return {"type": "error", "error": "Invalid room"}

    async def _handle_get_state(self) -> dict[str, Any]:
        """Get current state for browser.

        Returns:
            Current state data
        """
        return {
            "type": "state",
            "connected": self.client is not None,
            "hub_name": self.hub_name,
            "nickname": self.client.nickname if self.client else None,
            "identity_hash": self.identity.hash.hex() if self.identity else None,
            "active_room": self.active_room,
            "config": {
                "dest_name": self.config.get("dest_name", ""),
                "hub_hash": self.config.get("hub_hash", ""),
                "nickname": self.config.get("nickname", ""),
                "identity_path": self.config.get("identity_path", ""),
            },
            "rooms": {
                name: {
                    "messages": room_data["messages"][-STATE_MESSAGES_TO_RETURN:],
                    "users": list(room_data["users"]),
                }
                for name, room_data in self.rooms.items()
            },
        }

    async def _handle_get_discovered_hubs(self) -> dict[str, Any]:
        """Handle request for discovered hubs list.

        Returns:
            List of discovered hubs
        """
        self.cleanup_stale_hubs()

        return {"type": "discovered_hubs", "hubs": list(self.discovered_hubs.values())}

    async def _handle_send_command(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle send command request from browser.

        Args:
            data: Command parameters

        Returns:
            Response data
        """
        try:
            command = data.get("command")
            room = data.get("room", "[Hub]")

            if not isinstance(command, str) or len(command) > 10000:
                return {"type": "error", "error": "Invalid command"}

            if not isinstance(room, str) or len(room) > 64:
                return {"type": "error", "error": "Invalid room name"}

            if not self.client:
                return {"type": "error", "error": "Not connected to hub"}

            from .utils import normalize_room_name, sanitize_text_input

            normalized_room = normalize_room_name(room)
            if not normalized_room:
                return {"type": "error", "error": "Invalid room name"}

            sanitized_command = sanitize_text_input(command)
            if not sanitized_command:
                return {"type": "error", "error": "Invalid command"}

            await asyncio.get_event_loop().run_in_executor(
                None, self.client.msg, normalized_room, sanitized_command
            )

            return {"type": "command_sent"}
        except ValueError as e:
            logger.error("Invalid command data: %s", e)
            return {"type": "error", "error": f"Invalid command: {e}"}
        except Exception as e:
            logger.exception("Unexpected error sending command: %s", e)
            return {"type": "error", "error": str(e)}

    async def _handle_set_nickname(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle set nickname request from browser.

        Args:
            data: Nickname parameters

        Returns:
            Response data
        """
        try:
            nickname = data.get("nickname")

            if not isinstance(nickname, str) or len(nickname) > 32:
                return {"type": "error", "error": "Invalid nickname (max 32 characters)"}

            if not self.client:
                return {"type": "error", "error": "Not connected to hub"}

            self.client.nickname = nickname if nickname else None

            self.config["nickname"] = nickname
            save_config(self.config)

            return {"type": "nickname_set", "nickname": nickname}
        except Exception as e:
            logger.exception("Unexpected error setting nickname: %s", e)
            return {"type": "error", "error": str(e)}

    async def _on_message(self, env: dict) -> None:
        """Handle incoming message from RRC."""
        try:
            ts = env.get(K_TS)
            if isinstance(ts, int):
                current_time_ms = int(time.time() * 1000)
                skew_ms = MAX_TIMESTAMP_SKEW_SECONDS * 1000
                if abs(ts - current_time_ms) > skew_ms:
                    logger.warning(f"Message timestamp out of acceptable range: {ts}")

            room = env.get(K_ROOM, "[Hub]")
            src = env.get(K_SRC, b"")
            body = env.get(K_BODY, "")
            nick = env.get(K_NICK)

            nickname_changed = False
            if isinstance(src, (bytes, bytearray)) and isinstance(nick, str) and nick:
                from .utils import sanitize_display_name

                sanitized_nick = sanitize_display_name(nick, max_length=32)
                if sanitized_nick:
                    src_hex = src.hex()
                    with self._lock:
                        old_nick = self.nicknames.get(src_hex)
                        if old_nick != sanitized_nick:
                            self.nicknames[src_hex] = sanitized_nick
                            nickname_changed = True

            user = self._format_user(src)

            with self._lock:
                if room not in self.rooms:
                    if len(self.rooms) >= self.max_rooms:
                        logger.warning(
                            f"Room limit reached ({self.max_rooms}), ignoring message for new room: {room}"
                        )
                        return
                    self.rooms[room] = {"messages": [], "users": set()}

                if isinstance(src, (bytes, bytearray)):
                    src_hex = src.hex()
                    self.rooms[room]["users"].add(src_hex)

            msg_id = env.get(K_ID)
            message = {
                "type": "message",
                "room": room,
                "user": user,
                "text": body,
                "timestamp": self._get_timestamp(),
                "message_id": msg_id.hex() if isinstance(msg_id, (bytes, bytearray)) else None,
                "sender_identity": src.hex() if isinstance(src, (bytes, bytearray)) else None,
            }
            with self._lock:
                self.rooms[room]["messages"].append(message)
                if len(self.rooms[room]["messages"]) > self.max_messages_per_room:
                    self.rooms[room]["messages"] = self.rooms[room]["messages"][
                        -self.max_messages_per_room :
                    ]

            if nickname_changed and self.broadcast:
                with self._lock:
                    users = [self._format_user(bytes.fromhex(u)) for u in self.rooms[room]["users"]]
                await self.broadcast(
                    {
                        "type": "user_list_update",
                        "room": room,
                        "users": users,
                    }
                )

            if self.broadcast:
                await self.broadcast(message)
        except Exception as e:
            logger.exception(f"Error in _on_message: {e}")

    async def _on_notice(self, env: dict) -> None:
        """Handle incoming notice from RRC."""
        ts = env.get(K_TS)
        if isinstance(ts, int):
            current_time_ms = int(time.time() * 1000)
            skew_ms = MAX_TIMESTAMP_SKEW_SECONDS * 1000
            if abs(ts - current_time_ms) > skew_ms:
                logger.warning(f"Notice timestamp out of acceptable range: {ts}")

        room = env.get(K_ROOM)
        body = env.get(K_BODY, "")

        logger.info(f"Received notice for room '{room}': {body[:100] if body else '(empty)'}...")

        message = {
            "type": "notice",
            "room": room or "[Hub]",
            "text": body,
            "timestamp": self._get_timestamp(),
        }

        target_room = room or "[Hub]"
        if target_room not in self.rooms:
            if len(self.rooms) >= self.max_rooms:
                logger.warning(
                    f"Room limit reached ({self.max_rooms}), ignoring notice for new room: {target_room}"
                )
                return
            self.rooms[target_room] = {"messages": [], "users": set()}

        with self._lock:
            self.rooms[target_room]["messages"].append(message)
            if len(self.rooms[target_room]["messages"]) > self.max_messages_per_room:
                self.rooms[target_room]["messages"] = self.rooms[target_room]["messages"][
                    -self.max_messages_per_room :
                ]

        if self.broadcast:
            await self.broadcast(message)

    async def _on_error(self, env: dict) -> None:
        """Handle error from RRC."""
        body = env.get(K_BODY, "Unknown error")
        room = env.get(K_ROOM)

        message = {
            "type": "error",
            "room": room or "[Hub]",
            "text": body,
            "timestamp": self._get_timestamp(),
        }

        if self.broadcast:
            await self.broadcast(message)

    async def _on_welcome(self, env: dict) -> None:
        """Handle WELCOME from RRC."""
        body = env.get(K_BODY)
        if isinstance(body, dict):
            hub_name = body.get(B_WELCOME_HUB)
            if isinstance(hub_name, str) and hub_name:
                self.hub_name = hub_name
                logger.info(f"Connected to hub: {hub_name}")

        message = {
            "type": "notice",
            "room": "[Hub]",
            "text": f"Connected to hub{': ' + self.hub_name if self.hub_name else ''}",
            "timestamp": self._get_timestamp(),
        }

        if "[Hub]" not in self.rooms:
            self.rooms["[Hub]"] = {"messages": [], "users": set()}
        self.rooms["[Hub]"]["messages"].append(message)

        if self.broadcast:
            await self.broadcast(message)
            if self.hub_name:
                await self.broadcast(
                    {
                        "type": "hub_info",
                        "hub_name": self.hub_name,
                    }
                )

        if self.loop and not self.ping_task:
            self.ping_task = self.loop.create_task(self._ping_loop())

    async def _on_joined(self, room: str, env: dict) -> None:
        """Handle JOINED confirmation from RRC.

        This handles two scenarios:
        1. Self-join: Multiple hashes (full member list) - we just joined the room
        2. Member-join: Single hash - another user joined the room we're in
        """
        body = env.get(K_BODY)

        logger.debug(f"JOINED room={room}, body type={type(body)}, body={body}")

        # Extract user list from body (could be dict or list)
        user_list = None
        if isinstance(body, dict):
            user_list = body.get(B_JOINED_USERS)
            logger.debug(f"Body is dict, user_list={user_list}")
        elif isinstance(body, list):
            user_list = body
            logger.debug(f"Body is list directly, user_list={user_list}")

        if not isinstance(user_list, list):
            user_list = []

        # Determine if this is a self-join (multiple users) or member-join (single user)
        is_self_join = len(user_list) != 1

        if is_self_join:
            # We're joining the room - create/reset room with full member list
            if room not in self.rooms:
                if len(self.rooms) >= self.max_rooms:
                    logger.error(f"Room limit reached ({self.max_rooms}), cannot join room: {room}")
                    if self.broadcast:
                        await self.broadcast(
                            {
                                "type": "error",
                                "error": f"Cannot join room: server room limit reached ({self.max_rooms})",
                            }
                        )
                    return
                self.rooms[room] = {"messages": [], "users": set()}

            users = []
            for user_hash in user_list:
                if isinstance(user_hash, (bytes, bytearray)):
                    user_hex = user_hash.hex()
                    self.rooms[room]["users"].add(user_hex)
                    users.append(self._format_user(user_hash))
                    logger.debug(f"Added user: {self._format_user(user_hash)}")

            message = {
                "type": "system",
                "room": room,
                "text": f"Joined room: {room}",
                "timestamp": self._get_timestamp(),
            }
            self.rooms[room]["messages"].append(message)

            if self.broadcast:
                await self.broadcast(message)
                await self.broadcast(
                    {
                        "type": "room_joined",
                        "room": room,
                        "users": users,
                    }
                )
        else:
            # Another user joined the room we're already in
            if room not in self.rooms:
                logger.warning(f"Received JOINED for unknown room: {room}")
                return

            user_hash = user_list[0]
            if isinstance(user_hash, (bytes, bytearray)):
                user_hex = user_hash.hex()

                # Add user to room member list
                self.rooms[room]["users"].add(user_hex)
                user_formatted = self._format_user(user_hash)

                # Create join notification message
                message = {
                    "type": "join",
                    "room": room,
                    "user": user_formatted,
                    "timestamp": self._get_timestamp(),
                }
                self.rooms[room]["messages"].append(message)

                if self.broadcast:
                    await self.broadcast(message)
                    # Also send user list update
                    users = [self._format_user(bytes.fromhex(u)) for u in self.rooms[room]["users"]]
                    await self.broadcast(
                        {
                            "type": "user_list_update",
                            "room": room,
                            "users": users,
                        }
                    )

    async def _on_parted(self, room: str, env: dict) -> None:
        """Handle PARTED confirmation from RRC.

        This handles two scenarios:
        1. Self-part: Multiple hashes (remaining members) - we left the room
        2. Member-part: Single hash - another user left the room we're in
        """
        body = env.get(K_BODY)

        logger.debug(f"PARTED room={room}, body type={type(body)}, body={body}")

        # Extract user list from body (could be dict or list)
        user_list = None
        if isinstance(body, dict):
            user_list = body.get(B_JOINED_USERS)  # Reuse same key for remaining members
            logger.debug(f"Body is dict, user_list={user_list}")
        elif isinstance(body, list):
            user_list = body
            logger.debug(f"Body is list directly, user_list={user_list}")

        if not isinstance(user_list, list):
            user_list = []

        # Determine if this is a self-part (we left) or member-part (single user left)
        is_self_part = len(user_list) != 1

        if is_self_part:
            # We left the room
            message = {
                "type": "system",
                "room": room,
                "text": f"Left room: {room}",
                "timestamp": self._get_timestamp(),
            }

            if room in self.rooms:
                self.rooms[room]["messages"].append(message)

            if self.broadcast:
                await self.broadcast(message)
                await self.broadcast(
                    {
                        "type": "room_parted",
                        "room": room,
                    }
                )
        else:
            # Another user left the room we're in
            if room not in self.rooms:
                logger.warning(f"Received PARTED for unknown room: {room}")
                return

            user_hash = user_list[0]
            if isinstance(user_hash, (bytes, bytearray)):
                user_hex = user_hash.hex()
                user_formatted = self._format_user(user_hash)

                # Remove user from room member list
                self.rooms[room]["users"].discard(user_hex)

                # Create part notification message
                message = {
                    "type": "part",
                    "room": room,
                    "user": user_formatted,
                    "timestamp": self._get_timestamp(),
                }
                self.rooms[room]["messages"].append(message)

                if self.broadcast:
                    await self.broadcast(message)
                    # Also send user list update
                    users = [self._format_user(bytes.fromhex(u)) for u in self.rooms[room]["users"]]
                    await self.broadcast(
                        {
                            "type": "user_list_update",
                            "room": room,
                            "users": users,
                        }
                    )

    async def _on_close(self) -> None:
        """Handle connection close from RRC."""
        if self.ping_task:
            self.ping_task.cancel()
            self.ping_task = None
        self.latency_ms = None

        message = {
            "type": "system",
            "room": "[Hub]",
            "text": "Disconnected from hub",
            "timestamp": self._get_timestamp(),
        }

        if self.broadcast:
            await self.broadcast(message)
            await self.broadcast({"type": "disconnected"})

    async def _on_pong(self, _env: dict) -> None:
        """Handle PONG response from hub.

        Args:
            _env: PONG envelope
        """
        if self.last_ping_time:
            latency = int((time.time() - self.last_ping_time) * 1000)
            self.latency_ms = latency

            if self.broadcast:
                await self.broadcast({"type": "latency", "latency_ms": latency})

    async def _ping_loop(self) -> None:
        """Background task to send periodic pings for latency monitoring."""
        try:
            while True:
                await asyncio.sleep(30)

                if self.client:
                    self.last_ping_time = time.time()
                    try:
                        await asyncio.get_event_loop().run_in_executor(None, self.client.ping)
                    except Exception as e:
                        logger.error(f"Error sending ping: {e}")
                        self.latency_ms = None
                        if self.broadcast:
                            await self.broadcast({"type": "latency", "latency_ms": None})
        except asyncio.CancelledError:
            logger.debug("Ping task cancelled")
            raise

    def load_discovered_hubs(self) -> None:
        """Load discovered hubs from cache file with validation."""
        try:
            if self.hub_cache_path.exists():
                file_size = self.hub_cache_path.stat().st_size
                if file_size > 1024 * 1024:
                    logger.warning("Hub cache file too large: %d bytes, resetting", file_size)
                    self.discovered_hubs = {}
                    return

                with open(self.hub_cache_path, encoding="utf-8") as f:
                    data = json.load(f)

                if not isinstance(data, dict):
                    logger.warning("Hub cache has invalid format, resetting")
                    self.discovered_hubs = {}
                    return

                validated_hubs = {}
                for hash_hex, hub in data.items():
                    if not isinstance(hub, dict):
                        continue

                    if not all(key in hub for key in ["hash", "name", "last_seen"]):
                        logger.debug(f"Skipping invalid hub entry: {hash_hex}")
                        continue

                    if not isinstance(hash_hex, str) or len(hash_hex) != len(hub.get("hash", "")):
                        continue

                    last_seen = hub.get("last_seen")
                    if not isinstance(last_seen, (int, float)):
                        continue

                    current_time = time.time()
                    if last_seen < 0 or last_seen > current_time + MAX_TIMESTAMP_SKEW_SECONDS:
                        logger.debug(f"Skipping hub with invalid timestamp: {last_seen}")
                        continue

                    validated_hubs[hash_hex] = hub

                self.discovered_hubs = validated_hubs
                logger.info(f"Loaded {len(self.discovered_hubs)} discovered hub(s) from cache")
            else:
                logger.debug("No hub cache file found, starting with empty list")
        except json.JSONDecodeError as e:
            logger.error(f"Hub cache file is corrupted: {e}")
            self.discovered_hubs = {}
        except Exception as e:
            logger.error(f"Failed to load discovered hubs: {e}")
            self.discovered_hubs = {}

    def save_discovered_hubs(self) -> None:
        """Save discovered hubs to cache file."""
        try:
            self.hub_cache_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.hub_cache_path, "w", encoding="utf-8") as f:
                json.dump(self.discovered_hubs, f, indent=2)
            logger.debug(f"Saved {len(self.discovered_hubs)} discovered hub(s) to cache")
        except Exception as e:
            logger.error(f"Failed to save discovered hubs: {e}")

    def cleanup_stale_hubs(self) -> None:
        """Remove hubs that haven't been seen in over 1 hour."""
        current_time = time.time()
        stale_threshold = STALE_HUB_THRESHOLD_SECONDS

        stale_hubs = [
            hash_hex
            for hash_hex, hub in self.discovered_hubs.items()
            if current_time - hub.get("last_seen", 0) > stale_threshold
        ]

        for hash_hex in stale_hubs:
            del self.discovered_hubs[hash_hex]

        if stale_hubs:
            logger.info(f"Removed {len(stale_hubs)} stale hub(s) from cache")
            self.save_discovered_hubs()

    def _format_user(self, src: bytes | bytearray) -> str:
        """Format user for display.

        Args:
            src: User identity hash

        Returns:
            Formatted user string
        """
        if isinstance(src, (bytes, bytearray)):
            src_hex = src.hex()
            with self._lock:
                nick = self.nicknames.get(src_hex)
            if nick:
                return f"{nick} ({src_hex[:8]})"
            return f"{src_hex[:16]}..."
        return "Unknown"

    def _check_room_operation_rate_limit(self, operation_key: str) -> bool:
        """Check if room operation is within rate limit.

        Args:
            operation_key: Unique key for this operation (e.g., 'join:room_name')

        Returns:
            True if operation is allowed, False if rate limited
        """
        now = time.time()
        with self._lock:
            if operation_key not in self.room_operation_times:
                self.room_operation_times[operation_key] = []

            self.room_operation_times[operation_key] = [
                t
                for t in self.room_operation_times[operation_key]
                if now - t < self.room_op_rate_window
            ]

            if len(self.room_operation_times[operation_key]) >= self.room_op_rate_limit:
                return False

            self.room_operation_times[operation_key].append(now)
            return True

    def _get_timestamp(self) -> str:
        """Get current timestamp.

        Returns:
            Formatted timestamp
        """
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S")
