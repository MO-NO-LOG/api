from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError

from app.services.base import valkey_operation
from app.utils import decode_token


class TokenBlacklistService:
    """
    Service for managing token blacklist using Valkey.

    Blacklisted tokens are stored with their remaining TTL (time-to-live)
    to automatically expire when the original token would have expired.
    """

    BLACKLIST_PREFIX = "blacklist:"

    @staticmethod
    @valkey_operation
    async def add_to_blacklist(client, token: str) -> bool:
        """
        Add a token to the blacklist.

        Args:
            token: JWT token to blacklist

        Returns:
            True if successfully added, False otherwise
        """
        try:
            # Decode token to get expiration time
            payload = decode_token(token)
            exp_timestamp = payload.get("exp")

            if not exp_timestamp:
                return False

            # Calculate remaining TTL
            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            ttl_seconds = int((exp_datetime - now).total_seconds())

            # Only blacklist if token hasn't expired yet
            if ttl_seconds > 0:
                key = f"{TokenBlacklistService.BLACKLIST_PREFIX}{token}"
                await client.setex(key, ttl_seconds, "blacklisted")
                return True

            return False

        except (JWTError, Exception) as e:
            print(f"Error adding token to blacklist: {e}")
            return False

    @staticmethod
    @valkey_operation
    async def is_blacklisted(client, token: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token: JWT token to check

        Returns:
            True if token is blacklisted, False otherwise
        """
        try:
            key = f"{TokenBlacklistService.BLACKLIST_PREFIX}{token}"
            result = await client.exists(key)
            return bool(result > 0)
        except Exception as e:
            print(f"Error checking blacklist: {e}")
            # Fail open - if Valkey is down, allow the request
            # (token validation will still happen via JWT signature)
            return False

    @staticmethod
    @valkey_operation
    async def remove_from_blacklist(client, token: str) -> bool:
        """
        Remove a token from the blacklist (rarely used).

        Args:
            token: JWT token to remove

        Returns:
            True if successfully removed, False otherwise
        """
        try:
            key = f"{TokenBlacklistService.BLACKLIST_PREFIX}{token}"
            result = await client.delete(key)
            return bool(result > 0)
        except Exception as e:
            print(f"Error removing token from blacklist: {e}")
            return False


class RefreshTokenService:
    """
    Service for managing refresh tokens using Valkey.

    Refresh tokens are stored with user email as key to allow
    single-device or multi-device session management.
    """

    REFRESH_TOKEN_PREFIX = "refresh_token:"

    @staticmethod
    @valkey_operation
    async def store_refresh_token(
        client,
        email: str,
        refresh_token: str,
        expires_delta: Optional[timedelta] = None,
    ) -> bool:
        """
        Store a refresh token for a user.

        Args:
            email: User's email
            refresh_token: The refresh token to store
            expires_delta: Optional custom expiration time

        Returns:
            True if successfully stored, False otherwise
        """
        try:
            if expires_delta:
                ttl_seconds = int(expires_delta.total_seconds())
            else:
                from app.config import settings

                ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

            key = f"{RefreshTokenService.REFRESH_TOKEN_PREFIX}{email}"
            await client.setex(key, ttl_seconds, refresh_token)
            return True

        except Exception as e:
            print(f"Error storing refresh token: {e}")
            return False

    @staticmethod
    @valkey_operation
    async def get_refresh_token(client, email: str) -> Optional[str]:
        """
        Get the stored refresh token for a user.

        Args:
            email: User's email

        Returns:
            Refresh token if exists, None otherwise
        """
        try:
            key = f"{RefreshTokenService.REFRESH_TOKEN_PREFIX}{email}"
            result = await client.get(key)
            return str(result) if result else None
        except Exception as e:
            print(f"Error getting refresh token: {e}")
            return None

    @staticmethod
    async def verify_refresh_token(email: str, refresh_token: str) -> bool:
        """
        Verify if the provided refresh token matches the stored one.

        Args:
            email: User's email
            refresh_token: Refresh token to verify

        Returns:
            True if tokens match, False otherwise
        """
        try:
            stored_token = await RefreshTokenService.get_refresh_token(email)
            return stored_token == refresh_token if stored_token else False
        except Exception as e:
            print(f"Error verifying refresh token: {e}")
            return False

    @staticmethod
    @valkey_operation
    async def delete_refresh_token(client, email: str) -> bool:
        """
        Delete a user's refresh token (e.g., on logout).

        Args:
            email: User's email

        Returns:
            True if successfully deleted, False otherwise
        """
        try:
            key = f"{RefreshTokenService.REFRESH_TOKEN_PREFIX}{email}"
            result = await client.delete(key)
            return bool(result > 0)
        except Exception as e:
            print(f"Error deleting refresh token: {e}")
            return False
