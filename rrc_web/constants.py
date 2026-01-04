"""RRC protocol constants (numeric keys and message types).

RRC Protocol v1.0
=================

This module defines the constants for the RRC (Reticulum Relay Chat) protocol.
All envelope keys are integers to minimize overhead in CBOR encoding.

Protocol Version Compatibility:
    - RRC_VERSION = 1: Initial protocol version
    - Clients MUST validate protocol version before processing envelopes
    - Future versions may add new message types or keys but MUST remain backward compatible
"""

# Protocol version - must match between client and hub
RRC_VERSION = 1

# ============================================================================
# Envelope Keys (All Required Unless Noted)
# ============================================================================

K_V = 0  # Protocol version (int) - REQUIRED, must equal RRC_VERSION
K_T = 1  # Message type (int) - REQUIRED, one of T_* constants below
K_ID = 2  # Message ID (bytes, 8 bytes) - REQUIRED, unique per message
K_TS = 3  # Timestamp (int, milliseconds since epoch) - REQUIRED
K_SRC = 4  # Source identity hash (bytes) - REQUIRED, sender's RNS identity hash
K_ROOM = 5  # Room name (str) - OPTIONAL, lowercase normalized room name
K_BODY = 6  # Message body (varies by type) - OPTIONAL, type-specific payload
K_NICK = 7  # Nickname (str) - OPTIONAL, human-readable sender name

# ============================================================================
# Message Types - Connection Lifecycle (1-9)
# ============================================================================

T_HELLO = 1  # Client -> Hub: Initial handshake with capabilities
# Body: dict with B_HELLO_* keys
# Response: T_WELCOME or T_ERROR

T_WELCOME = 2  # Hub -> Client: Connection accepted, hub info provided
# Body: dict with B_WELCOME_* keys
# Marks successful connection establishment

# ============================================================================
# Message Types - Room Management (10-19)
# ============================================================================

T_JOIN = 10  # Client -> Hub: Request to join a room
# Room: target room name (required)
# Body: optional room key/password (str or None)
# Response: T_JOINED or T_ERROR

T_JOINED = 11  # Hub -> Client: Confirmation of room join
# Room: joined room name
# Body: dict with B_JOINED_* keys (user list)

T_PART = 12  # Client -> Hub: Request to leave a room
# Room: target room name (required)
# Response: T_PARTED or T_ERROR

T_PARTED = 13  # Hub -> Client: Confirmation of room departure
# Room: parted room name

# ============================================================================
# Message Types - Chat Messages (20-29)
# ============================================================================

T_MSG = 20  # Client -> Hub or Hub -> Client: Regular chat message
# Room: target room (required)
# Body: message text (str)
# Broadcast to all users in the room

T_NOTICE = 21  # Hub -> Client: System notice or announcement
# Room: target room (optional, None = hub-level notice)
# Body: notice text (str) or delivered via Resource

# ============================================================================
# Message Types - Connection Monitoring (30-39)
# ============================================================================

T_PING = 30  # Bidirectional: Request latency check
# Body: optional echo data
# Response: T_PONG with same body

T_PONG = 31  # Bidirectional: Response to PING
# Body: echo data from PING

# ============================================================================
# Message Types - Error Handling (40-49)
# ============================================================================

T_ERROR = 40  # Hub -> Client: Error response
# Room: related room (optional)
# Body: error message (str)

# ============================================================================
# Message Types - Resource Transfers (50-59)
# ============================================================================

T_RESOURCE_ENVELOPE = 50  # Hub -> Client: Announces incoming Resource transfer
# Body: dict with B_RES_* keys
# Client uses this to prepare for RNS Resource reception

# ============================================================================
# HELLO Body Keys (Client Capabilities)
# ============================================================================

B_HELLO_NAME = 0  # Client software name (str) e.g., "rrc-browser"
B_HELLO_VER = 1  # Client software version (str) e.g., "0.1.0"
B_HELLO_CAPS = 2  # Capabilities dict (dict[int, bool]) - keys are CAP_* constants

# ============================================================================
# WELCOME Body Keys (Hub Information)
# ============================================================================

B_WELCOME_HUB = 0  # Hub name (str) - human-readable hub identifier
B_WELCOME_VER = 1  # Hub software version (str)
B_WELCOME_CAPS = 2  # Hub capabilities dict (dict[int, bool])

# ============================================================================
# JOINED Body Keys (Room State)
# ============================================================================

B_JOINED_USERS = 0  # List of user identity hashes (list[bytes]) in the room

# ============================================================================
# Capability Flags (Used in HELLO/WELCOME caps dicts)
# ============================================================================

CAP_RESOURCE_ENVELOPE = 0  # Support for large message delivery via RNS Resources
# If true, hub may send T_RESOURCE_ENVELOPE before Resource

# ============================================================================
# RESOURCE_ENVELOPE Body Keys (Resource Transfer Metadata)
# ============================================================================

B_RES_ID = 0  # Resource ID (bytes) - unique identifier for matching
B_RES_KIND = 1  # Resource kind (str) - one of RES_KIND_* constants
B_RES_SIZE = 2  # Resource size (int) - bytes, for validation
B_RES_SHA256 = 3  # SHA-256 hash (bytes, 32 bytes) - OPTIONAL, for integrity check
B_RES_ENCODING = 4  # Text encoding (str) - OPTIONAL, e.g., "utf-8" for text resources

# ============================================================================
# Resource Kinds (Types of Resource Transfers)
# ============================================================================

RES_KIND_NOTICE = "notice"  # Large notice/announcement as text resource
RES_KIND_MOTD = "motd"  # Message of the day as text resource
RES_KIND_BLOB = "blob"  # Binary data (future use)
