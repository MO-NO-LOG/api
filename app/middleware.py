from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.security import (
    create_csrf_token_with_signature,
    generate_csrf_token,
    set_csrf_cookie,
    validate_csrf_tokens,
)
from app.services.rate_limit_service import RateLimitService


class CsrfMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection Middleware using Double Submit Cookie pattern.

    Security mechanism:
    1. For GET/HEAD/OPTIONS: Always ensure CSRF cookie is present
    2. For state-changing methods (POST/PUT/PATCH/DELETE):
       - If user is authenticated (has auth cookie), validate CSRF tokens
       - Cookie token must match header token
       - Uses HMAC-based signature for additional security

    Exception paths (no CSRF check):
    - /api/auth/login - Initial login doesn't have CSRF token yet
    - /api/auth/register - Registration endpoint
    - /api/auth/verify-email/* - Email verification endpoints
    - /api/auth/csrf - CSRF token generation endpoint
    """

    # Paths that don't require CSRF validation
    CSRF_EXEMPT_PATHS = {
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/verify-email/send",
        "/api/auth/verify-email/confirm",
        "/api/auth/verify-email/status",
        "/api/auth/csrf",
    }

    # Safe HTTP methods that don't modify state
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

    async def dispatch(self, request: Request, call_next: Callable):
        # Skip CSRF check for safe methods
        if request.method in self.SAFE_METHODS:
            response = await call_next(request)
            # Ensure CSRF cookie exists for all responses
            if not request.cookies.get(settings.CSRF_COOKIE_NAME):
                token = generate_csrf_token()
                signed_token = create_csrf_token_with_signature(token)
                set_csrf_cookie(response, signed_token)
            return response

        # Skip CSRF check for exempt paths
        path = request.url.path
        if self._is_exempt_path(path):
            response = await call_next(request)
            # Set CSRF token for login/register responses
            if path in {"/api/auth/login", "/api/auth/register"}:
                token = generate_csrf_token()
                signed_token = create_csrf_token_with_signature(token)
                set_csrf_cookie(response, signed_token)
            return response

        # Check if user is authenticated via Authorization header
        auth_header = request.headers.get("Authorization")
        is_authenticated = bool(auth_header and auth_header.startswith("Bearer "))

        if is_authenticated:
            # User is authenticated, validate CSRF tokens
            header_token = request.headers.get(settings.CSRF_HEADER_NAME)
            cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)

            if not validate_csrf_tokens(cookie_token, header_token):
                return JSONResponse(
                    status_code=403,
                    content={
                        "code": "CSRF_INVALID",
                        "message": "CSRF token validation failed. Token is missing, invalid, or expired.",
                        "details": {
                            "has_cookie": bool(cookie_token),
                            "has_header": bool(header_token),
                        },
                    },
                )

        # Process request
        response = await call_next(request)

        # Ensure CSRF cookie exists in response
        if not request.cookies.get(settings.CSRF_COOKIE_NAME):
            token = generate_csrf_token()
            signed_token = create_csrf_token_with_signature(token)
            set_csrf_cookie(response, signed_token)

        return response

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from CSRF validation."""
        return path in self.CSRF_EXEMPT_PATHS


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse.

    Uses Valkey for distributed rate limiting.
    Rate limits are applied per IP + path combination.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Create rate limit key
        key = f"rate_limit:{client_ip}:{request.url.path}"

        # Check rate limit
        allowed = await RateLimitService.allow(
            key,
            settings.RATE_LIMIT_MAX_REQUESTS,
            settings.RATE_LIMIT_WINDOW_SECONDS,
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "code": "RATE_LIMITED",
                    "message": f"Too many requests. Maximum {settings.RATE_LIMIT_MAX_REQUESTS} requests per {settings.RATE_LIMIT_WINDOW_SECONDS} seconds.",
                    "retry_after": settings.RATE_LIMIT_WINDOW_SECONDS,
                },
                headers={
                    "Retry-After": str(settings.RATE_LIMIT_WINDOW_SECONDS),
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_MAX_REQUESTS),
                    "X-RateLimit-Window": str(settings.RATE_LIMIT_WINDOW_SECONDS),
                },
            )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains (HTTPS only)
    - Content-Security-Policy: Restrictive CSP
    """

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Enforce HTTPS (only in production)
        if settings.COOKIE_SECURE:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Adjust based on your needs
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )

        return response
