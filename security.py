"""Security middleware and utilities for the application"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import time
from collections import defaultdict
import hashlib
import secrets
from datetime import datetime, timedelta

# Rate limiting: token -> (request_count, window_start)
rate_limit_store = defaultdict(lambda: {"count": 0, "window_start": time.time()})

# CSRF tokens: session_id -> token
csrf_store = defaultdict(str)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent brute force attacks
    Limits requests per IP address
    """

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Get or create rate limit entry
        entry = rate_limit_store[client_ip]
        if current_time - entry["window_start"] > 60:  # 1-minute window
            entry["count"] = 0
            entry["window_start"] = current_time

        # Stricter limits for auth endpoints
        auth_endpoints = ["/auth/login", "/auth/register"]
        limit = 5 if any(request.url.path.startswith(ep) for ep in auth_endpoints) else 100

        if entry["count"] >= limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "status": "error",
                    "detail": "Too many requests. Please try again later.",
                },
            )

        entry["count"] += 1
        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses to prevent common attacks
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS protection (browser feature)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content Security Policy (basic)
        response.headers[
            "Content-Security-Policy"
        ] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # HSTS (only on HTTPS in production)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


def generate_csrf_token() -> str:
    """Generate a secure CSRF token"""
    return secrets.token_urlsafe(32)


def validate_csrf_token(session_id: str, provided_token: str) -> bool:
    """Validate a CSRF token for a session"""
    expected_token = csrf_store.get(session_id)
    if not expected_token:
        return False
    return secrets.compare_digest(expected_token, provided_token)


def hash_password_cost(password: str) -> str:
    """
    Calculate password hash cost metric for security analysis
    Not for actual hashing - use passlib/bcrypt for that
    """
    return hashlib.sha256(password.encode()).hexdigest()[:16]


def check_password_strength(password: str) -> dict:
    """
    Validate password strength requirements
    Returns {'is_valid': bool, 'errors': [str]}
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")

    if not any(c in "!@#$%^&*()_+-=[]{}';:\"\\|,.<>/?`~" for c in password):
        errors.append("Password must contain at least one special character")

    common_passwords = [
        "password",
        "password123",
        "admin",
        "123456",
        "qwerty",
        "welcome",
    ]
    if password.lower() in common_passwords:
        errors.append("Password is too common. Please choose a more unique password")

    return {"is_valid": len(errors) == 0, "errors": errors}


class SessionManager:
    """Secure session management with expiration"""

    def __init__(self, session_timeout_minutes: int = 30):
        self.session_timeout_minutes = session_timeout_minutes
        self.sessions = {}  # session_id -> {user_id, role, created_at, last_activity}

    def create_session(self, user_id: int, role: str) -> str:
        """Create a new secure session"""
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            "user_id": user_id,
            "role": role,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
        }
        return session_id

    def validate_session(self, session_id: str) -> dict | None:
        """Validate session and check for expiration"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        # Check timeout
        last_activity = session["last_activity"]
        if datetime.utcnow() - last_activity > timedelta(
            minutes=self.session_timeout_minutes
        ):
            self.sessions.pop(session_id, None)
            return None

        # Update last activity
        session["last_activity"] = datetime.utcnow()
        return session

    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session"""
        return self.sessions.pop(session_id, None) is not None

    def invalidate_user_sessions(self, user_id: int) -> int:
        """Invalidate all sessions for a user (logout everywhere)"""
        count = 0
        sessions_to_remove = [
            sid
            for sid, session in self.sessions.items()
            if session["user_id"] == user_id
        ]
        for sid in sessions_to_remove:
            self.sessions.pop(sid, None)
            count += 1
        return count
