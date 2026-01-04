"""Authentication and security middleware for RRC Web Client."""

from __future__ import annotations

import hmac
import logging
import secrets
import time
from collections import defaultdict
from typing import Any, cast

from aiohttp import web

logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "rrc_session"
MAX_SESSION_AGE_SECONDS = 3600

LOGIN_RATE_LIMIT_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW = 300
login_attempts: dict[str, list[float]] = defaultdict(list)


class AuthManager:
    """Manages authentication and sessions for the web server."""

    def __init__(self, auth_token: str, session_timeout_minutes: int = 60):
        """Initialize authentication manager.

        Args:
            auth_token: Secret token for authentication
            session_timeout_minutes: Session timeout in minutes
        """
        self.auth_token = auth_token
        self.session_timeout = session_timeout_minutes * 60
        self.sessions: dict[str, float] = {}
        self.secret_key = secrets.token_bytes(32)

    def generate_session_id(self) -> str:
        """Generate a secure session ID.

        Returns:
            Random session ID string
        """
        return secrets.token_urlsafe(32)

    def create_session(self) -> str:
        """Create a new session.

        Returns:
            Session ID
        """
        session_id = self.generate_session_id()
        self.sessions[session_id] = time.time()
        self._cleanup_expired_sessions()
        logger.info("Created new session: %s", session_id[:8] + "...")
        return session_id

    def validate_session(self, session_id: str | None) -> bool:
        """Validate a session ID.

        Args:
            session_id: Session ID to validate

        Returns:
            True if session is valid, False otherwise
        """
        if not session_id:
            return False

        if session_id not in self.sessions:
            return False

        session_age = time.time() - self.sessions[session_id]
        if session_age > self.session_timeout:
            logger.info("Session expired: %s", session_id[:8] + "...")
            del self.sessions[session_id]
            return False

        self.sessions[session_id] = time.time()
        return True

    def invalidate_session(self, session_id: str) -> None:
        """Invalidate a session.

        Args:
            session_id: Session ID to invalidate
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info("Invalidated session: %s", session_id[:8] + "...")

    def verify_token(self, token: str) -> bool:
        """Verify authentication token using constant-time comparison.

        Args:
            token: Token to verify

        Returns:
            True if token is valid, False otherwise
        """
        if not token or not self.auth_token:
            return False

        return hmac.compare_digest(token.encode(), self.auth_token.encode())

    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions."""
        current_time = time.time()
        expired = [
            sid
            for sid, created in self.sessions.items()
            if current_time - created > self.session_timeout
        ]
        for sid in expired:
            del self.sessions[sid]
        if expired:
            logger.info("Cleaned up %d expired sessions", len(expired))


@web.middleware
async def auth_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
    """Middleware to enforce authentication.

    Args:
        request: HTTP request
        handler: Request handler

    Returns:
        HTTP response
    """
    auth_manager: AuthManager | None = request.app.get("auth_manager")

    if not auth_manager:
        return cast(web.StreamResponse, await handler(request))

    allowed_paths = ["/", "/api/login", "/api/logout", "/api/auth-status"]
    static_extensions = (
        ".css",
        ".js",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
    )

    if (
        request.path in allowed_paths
        or request.path.startswith("/static/")
        or request.path.endswith(static_extensions)
    ):
        return cast(web.StreamResponse, await handler(request))

    session_id = request.cookies.get(SESSION_COOKIE_NAME)

    if not auth_manager.validate_session(session_id):
        if request.headers.get("Upgrade", "").lower() == "websocket":
            return web.Response(status=401, text="Unauthorized")

        return web.json_response({"error": "Unauthorized"}, status=401)

    request["session_id"] = session_id
    return cast(web.StreamResponse, await handler(request))


@web.middleware
async def security_headers_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
    """Middleware to add security headers.

    Args:
        request: HTTP request
        handler: Request handler

    Returns:
        HTTP response with security headers
    """
    response = await handler(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "connect-src 'self' ws: wss:",
        "font-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
    response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

    return cast(web.StreamResponse, response)


async def handle_login(request: web.Request) -> web.Response:
    """Handle login requests with rate limiting.

    Args:
        request: HTTP request

    Returns:
        HTTP response with session cookie or error
    """
    auth_manager: AuthManager | None = request.app.get("auth_manager")

    if not auth_manager:
        return web.json_response({"error": "Authentication not enabled"}, status=400)

    client_ip = request.remote or "unknown"
    current_time = time.time()

    login_attempts[client_ip] = [
        t for t in login_attempts[client_ip] if current_time - t < LOGIN_RATE_LIMIT_WINDOW
    ]

    if len(login_attempts[client_ip]) >= LOGIN_RATE_LIMIT_ATTEMPTS:
        logger.warning("Rate limit exceeded for login attempts from %s", client_ip)
        return web.json_response(
            {"error": "Too many login attempts. Please try again later."}, status=429
        )

    try:
        data = await request.json()
        token = data.get("token", "")
    except Exception:
        return web.json_response({"error": "Invalid request"}, status=400)

    if auth_manager.verify_token(token):
        login_attempts.pop(client_ip, None)

        session_id = auth_manager.create_session()

        response = web.json_response({"success": True})
        response.set_cookie(
            SESSION_COOKIE_NAME,
            session_id,
            max_age=auth_manager.session_timeout,
            httponly=True,
            secure=request.scheme == "https",
            samesite="Strict",
        )
        return response
    else:
        login_attempts[client_ip].append(current_time)
        logger.warning(
            "Failed login attempt from %s (%d attempts)", client_ip, len(login_attempts[client_ip])
        )
        return web.json_response({"error": "Invalid token"}, status=401)


async def handle_logout(request: web.Request) -> web.Response:
    """Handle logout requests.

    Args:
        request: HTTP request

    Returns:
        HTTP response
    """
    auth_manager: AuthManager | None = request.app.get("auth_manager")
    session_id = request.cookies.get(SESSION_COOKIE_NAME)

    if auth_manager and session_id:
        auth_manager.invalidate_session(session_id)

    response = web.json_response({"success": True})
    response.del_cookie(SESSION_COOKIE_NAME)
    return response


async def handle_auth_status(request: web.Request) -> web.Response:
    """Handle auth status check requests.

    Args:
        request: HTTP request

    Returns:
        HTTP response with auth status
    """
    auth_manager: AuthManager | None = request.app.get("auth_manager")
    session_id = request.cookies.get(SESSION_COOKIE_NAME)

    auth_required = auth_manager is not None

    is_authenticated = False
    if auth_manager and session_id:
        is_authenticated = auth_manager.validate_session(session_id)

    return web.json_response({"auth_required": auth_required, "is_authenticated": is_authenticated})
