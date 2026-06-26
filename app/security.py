import hashlib
import hmac
import secrets
from typing import Literal, Optional, Union

from fastapi import Response

from app.config import settings


def generate_csrf_token() -> str:
    """
    Generate a cryptographically secure CSRF token.
    Uses secrets module for secure random generation.
    """
    return secrets.token_urlsafe(settings.CSRF_TOKEN_BYTES)


def create_csrf_token_with_signature(token: str) -> str:
    """
    Create a signed CSRF token using HMAC for additional security.
    Format: token.signature
    """
    signature = hmac.new(
        settings.SECRET_KEY.encode(), token.encode(), hashlib.sha256
    ).hexdigest()
    return f"{token}.{signature}"


def verify_csrf_token_signature(signed_token: str) -> tuple[bool, Optional[str]]:
    """
    Verify the CSRF token signature.
    Returns: (is_valid, token)
    """
    try:
        parts = signed_token.rsplit(".", 1)
        if len(parts) != 2:
            return False, None

        token, signature = parts
        expected_signature = hmac.new(
            settings.SECRET_KEY.encode(), token.encode(), hashlib.sha256
        ).hexdigest()

        # Use constant-time comparison to prevent timing attacks
        if hmac.compare_digest(signature, expected_signature):
            return True, token
        return False, None
    except Exception:
        return False, None


def set_csrf_cookie(response: Response, token: str) -> None:
    """
    Set CSRF token cookie in response.
    Cookie is NOT httponly so JavaScript can read it.
    """
    samesite: Literal["lax", "strict", "none"] = "lax"
    if settings.COOKIE_SAMESITE in ("strict", "none"):
        samesite = settings.COOKIE_SAMESITE  # type: ignore

    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=token,
        httponly=False,  # Must be False so JS can read it
        max_age=settings.COOKIE_MAX_AGE_DAYS * 24 * 60 * 60,
        path=settings.COOKIE_PATH,
        samesite=samesite,
        secure=settings.COOKIE_SECURE,
        domain=settings.COOKIE_DOMAIN,
    )


def clear_csrf_cookie(response: Response) -> None:
    """
    Clear CSRF cookie only.
    """
    response.delete_cookie(
        key=settings.CSRF_COOKIE_NAME,
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
    )


def validate_csrf_tokens(
    cookie_token: Optional[str], header_token: Optional[str]
) -> bool:
    """
    Validate CSRF tokens using double-submit cookie pattern.
    Both tokens must be present and must match.
    If signature verification is enabled, verify signature as well.
    """
    if not cookie_token or not header_token:
        return False

    # Check if tokens use signature format
    if "." in cookie_token and "." in header_token:
        # Verify signatures
        cookie_valid, cookie_raw = verify_csrf_token_signature(cookie_token)
        header_valid, header_raw = verify_csrf_token_signature(header_token)

        if not cookie_valid or not header_valid:
            return False

        # Compare raw tokens using constant-time comparison
        return hmac.compare_digest(cookie_raw or "", header_raw or "")

    # Simple comparison for non-signed tokens (legacy support)
    return hmac.compare_digest(cookie_token, header_token)


def set_refresh_cookie(response: Response, refresh_token: str, max_age: int) -> None:
    """Set the HttpOnly refresh token cookie."""
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        max_age=max_age,
        httponly=settings.REFRESH_TOKEN_COOKIE_HTTPONLY,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,  # type: ignore[arg-type]
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
    )


def clear_refresh_cookie(response: Response) -> None:
    """Clear the HttpOnly refresh token cookie."""
    response.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
    )


def get_token_from_header_or_cookie(
    request, cookie_name: str, prefix: str = "Bearer "
) -> Union[str, None]:
    """Extract a bearer token from the Authorization header or a cookie."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith(prefix):
        return auth_header[len(prefix) :]

    cookie_token = request.cookies.get(cookie_name)
    if cookie_token and cookie_token.startswith(prefix):
        return cookie_token[len(prefix) :]

    return None
