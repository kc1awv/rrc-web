"""Main entry point for RRC browser client."""

import asyncio
import json
import logging
import os
import signal
import ssl
import sys
import time
import webbrowser
from collections import defaultdict
from pathlib import Path

from aiohttp import web

from .auth import (
    AuthManager,
    auth_middleware,
    handle_auth_status,
    handle_login,
    handle_logout,
    security_headers_middleware,
)
from .backend import BackendService

log_level = os.environ.get("RRC_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


MAX_WS_MESSAGE_SIZE = 1024 * 100
WS_RATE_LIMIT_MESSAGES = 20
WS_RATE_LIMIT_WINDOW = 1.0
ALLOWED_MESSAGE_TYPES = {
    "connect",
    "disconnect",
    "join_room",
    "part_room",
    "send_message",
    "send_command",
    "set_active_room",
    "set_nickname",
    "get_state",
    "get_discovered_hubs",
}


class HTTPServer:
    """HTTP server for serving static files and WebSocket endpoint."""

    MAX_WEBSOCKET_CONNECTIONS = 50

    def __init__(
        self,
        backend: BackendService,
        host: str = "localhost",
        port: int = 8080,
        config: dict | None = None,
        ssl_context: ssl.SSLContext | None = None,
    ):
        """Initialize HTTP server.

        Args:
            backend: Backend service instance
            host: Host to bind to
            port: Port to listen on
            config: Configuration dictionary
            ssl_context: SSL context for HTTPS
        """
        self.backend = backend
        self.host = host
        self.port = port
        self.config = config or {}
        self.ssl_context = ssl_context
        self.app = web.Application()
        self.websockets: set[web.WebSocketResponse] = set()
        self.ws_message_times: dict[web.WebSocketResponse, list[float]] = defaultdict(list)
        self.setup_middlewares()
        self.setup_middlewares()
        self.setup_routes()

    def setup_middlewares(self):
        """Set up middleware stack."""
        if self.config.get("enable_security_headers", True):
            self.app.middlewares.append(security_headers_middleware)

        if self.config.get("enable_auth", False):
            auth_token = self.config.get("auth_token", "")
            if auth_token:
                session_timeout = self.config.get("session_timeout_minutes", 60)
                auth_manager = AuthManager(auth_token, session_timeout)
                self.app["auth_manager"] = auth_manager
                self.app.middlewares.append(auth_middleware)
                logger.info("Authentication enabled")
            else:
                logger.warning(
                    "Authentication enabled but no auth_token configured. Disabling auth."
                )

    def setup_routes(self):
        """Set up HTTP routes."""
        static_dir = Path(__file__).parent / "static-svelte"

        self.app.router.add_static("/static", static_dir, name="static")

        self.app.router.add_get(
            "/{filename:.+\\.(png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)}",
            self.static_file_handler,
        )

        self.app.router.add_get("/", self.index_handler)
        self.app.router.add_get("/ws", self.websocket_handler)

        self.app.router.add_get("/api/auth-status", handle_auth_status)
        if self.config.get("enable_auth", False):
            self.app.router.add_post("/api/login", handle_login)
            self.app.router.add_post("/api/logout", handle_logout)

    async def index_handler(self, _request: web.Request) -> web.Response:
        """Serve the index.html page.

        Args:
            _request: HTTP request

        Returns:
            HTTP response with index.html
        """
        static_dir = Path(__file__).parent / "static-svelte"
        index_file = static_dir / "index.html"

        with open(index_file, encoding="utf-8") as f:
            html = f.read()

        return web.Response(text=html, content_type="text/html")

    async def static_file_handler(self, request: web.Request) -> web.Response:
        """Serve static files from the static-svelte directory.

        Args:
            request: HTTP request

        Returns:
            HTTP response with file content
        """
        filename = request.match_info["filename"]
        static_dir = Path(__file__).parent / "static-svelte"
        file_path = static_dir / filename

        try:
            file_path = file_path.resolve()
            static_dir = static_dir.resolve()
            if not str(file_path).startswith(str(static_dir)):
                return web.Response(status=404, text="Not found")
        except Exception:
            return web.Response(status=404, text="Not found")

        if not file_path.is_file():
            return web.Response(status=404, text="Not found")

        content_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
            ".woff": "font/woff",
            ".woff2": "font/woff2",
            ".ttf": "font/ttf",
            ".eot": "application/vnd.ms-fontobject",
        }
        suffix = file_path.suffix.lower()
        content_type = content_types.get(suffix, "application/octet-stream")

        with open(file_path, "rb") as f:
            content = f.read()

        return web.Response(body=content, content_type=content_type)

    async def websocket_handler(self, request: web.Request) -> web.StreamResponse:
        """Handle WebSocket connections.

        Args:
            request: WebSocket request

        Returns:
            WebSocket response
        """
        origin = request.headers.get("Origin")
        if origin:
            allowed_origins = set(self.config.get("allowed_origins", []))
            scheme = "https" if self.ssl_context else "http"
            allowed_origins.update(
                {
                    f"{scheme}://{self.host}:{self.port}",
                    f"{scheme}://localhost:{self.port}",
                    f"{scheme}://127.0.0.1:{self.port}",
                }
            )
            if origin not in allowed_origins:
                logger.warning(f"WebSocket connection rejected: invalid origin {origin}")
                return web.Response(status=403, text="Forbidden: Invalid origin")  # type: ignore[return-value]

        if len(self.websockets) >= self.MAX_WEBSOCKET_CONNECTIONS:
            logger.warning(
                f"WebSocket connection rejected: limit of {self.MAX_WEBSOCKET_CONNECTIONS} reached"
            )
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            await ws.send_json(
                {
                    "type": "error",
                    "error": f"Server is at maximum capacity ({self.MAX_WEBSOCKET_CONNECTIONS} connections)",
                }
            )
            await ws.close()
            return ws

        ws = web.WebSocketResponse(max_msg_size=MAX_WS_MESSAGE_SIZE)
        await ws.prepare(request)

        self.websockets.add(ws)

        logger.info(f"WebSocket client connected (total: {len(self.websockets)})")

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    now = time.time()
                    message_times = self.ws_message_times[ws]

                    message_times[:] = [t for t in message_times if now - t < WS_RATE_LIMIT_WINDOW]

                    if len(message_times) >= WS_RATE_LIMIT_MESSAGES:
                        logger.warning("Rate limit exceeded for WebSocket")
                        await ws.send_json(
                            {
                                "type": "error",
                                "error": "Rate limit exceeded. Please slow down.",
                            }
                        )
                        continue

                    message_times.append(now)

                    try:
                        data = json.loads(msg.data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON from WebSocket: {e}")
                        await ws.send_json({"type": "error", "error": "Invalid JSON format"})
                        continue

                    if not isinstance(data, dict):
                        logger.warning(f"WebSocket message is not a dict: {type(data)}")
                        await ws.send_json(
                            {"type": "error", "error": "Message must be a JSON object"}
                        )
                        continue

                    msg_type = data.get("type")
                    if not isinstance(msg_type, str) or msg_type not in ALLOWED_MESSAGE_TYPES:
                        logger.warning(f"Invalid message type: {msg_type}")
                        await ws.send_json({"type": "error", "error": "Invalid message type"})
                        continue

                    response = await self.backend.handle_ws_message(data)

                    if response:
                        await ws.send_json(response)

                elif msg.type == web.WSMsgType.ERROR:
                    logger.error("WebSocket error: %s", ws.exception())

        except asyncio.CancelledError:
            logger.info("WebSocket handler cancelled")
            raise
        except ConnectionResetError:
            logger.info("WebSocket connection reset by client")
        except Exception as e:
            logger.error("WebSocket handler error: %s", e, exc_info=True)
        finally:
            self.websockets.discard(ws)
            self.ws_message_times.pop(ws, None)
            logger.info("WebSocket client disconnected")

        return ws

    async def broadcast(self, data: dict):
        """Broadcast data to all connected WebSocket clients.

        Args:
            data: Data to broadcast
        """
        message = json.dumps(data)

        disconnected = set()
        for ws in self.websockets:
            try:
                await ws.send_str(message)
            except Exception as e:
                logger.error("Error broadcasting to WebSocket: %s", e)
                disconnected.add(ws)

        self.websockets -= disconnected

    async def start(self):
        """Start the HTTP server."""
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port, ssl_context=self.ssl_context)
        await site.start()

        scheme = "https" if self.ssl_context else "http"
        logger.info("%s server started on %s://%s:%d", scheme.upper(), scheme, self.host, self.port)


async def main_async(backend: BackendService):
    """Main async entry point.

    Args:
        backend: Pre-initialized backend service with Reticulum ready
    """
    config = backend.config

    port = int(os.environ.get("RRC_WEB_PORT", config.get("server_port", 8080)))
    host = config.get("server_host", "localhost")

    ssl_context = None
    if config.get("enable_ssl", False):
        cert_path = Path(config.get("ssl_cert_path", ""))
        key_path = Path(config.get("ssl_key_path", ""))

        if cert_path.exists() and key_path.exists():
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            try:
                ssl_context.load_cert_chain(cert_path, key_path)
                logger.info("SSL/TLS enabled")
            except Exception as e:
                logger.error("Failed to load SSL certificate: %s", e)
                logger.error("Continuing without SSL")
                ssl_context = None
        else:
            logger.warning("SSL enabled but certificate files not found")
            logger.warning("Use generate_cert.py to create certificates")
            logger.warning("Continuing without SSL")

    http_server = HTTPServer(backend, host=host, port=port, config=config, ssl_context=ssl_context)

    backend.broadcast = http_server.broadcast

    await backend.start()
    await http_server.start()

    scheme = "https" if ssl_context else "http"
    url = f"{scheme}://{host}:{port}"
    logger.info("Opening browser at %s", url)

    try:
        webbrowser.open(url)
    except Exception as e:
        logger.error("=" * 60)
        logger.error("COULD NOT OPEN BROWSER AUTOMATICALLY")
        logger.error("Error: %s", e)
        logger.error("")
        logger.error("Please manually open this URL in your browser:")
        logger.error("    %s", url)
        logger.error("=" * 60)
        print(f"\n>>> Please open this URL in your browser: {url} <<<\n")

    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    logger.info("RRC Browser started. Press Ctrl+C to stop.")
    await stop_event.wait()

    logger.info("Shutting down...")
    await backend.stop()


def main():
    """Main entry point."""
    try:
        backend = BackendService()
        backend.init_reticulum()

        asyncio.run(main_async(backend))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
