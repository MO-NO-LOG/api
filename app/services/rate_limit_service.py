from app.config import settings
from app.services.base import valkey_operation


class RateLimitService:
    PREFIX = "rl:"

    @staticmethod
    @valkey_operation
    async def allow(client, key: str, max_requests: int, window_seconds: int) -> bool:
        try:
            valkey_key = f"{RateLimitService.PREFIX}{key}"
            count = await client.incr(valkey_key)
            if count == 1:
                await client.expire(valkey_key, window_seconds)
            return count <= max_requests
        except Exception:
            return True


class LoginAttemptService:
    PREFIX = "login_attempts:"

    @staticmethod
    @valkey_operation
    async def register_failure(client, identifier: str) -> int:
        try:
            valkey_key = f"{LoginAttemptService.PREFIX}{identifier}"
            count = await client.incr(valkey_key)
            if count == 1:
                await client.expire(
                    valkey_key, settings.LOGIN_ATTEMPT_WINDOW_SECONDS
                )
            return int(count)
        except Exception:
            return 0

    @staticmethod
    @valkey_operation
    async def reset(client, identifier: str) -> None:
        try:
            valkey_key = f"{LoginAttemptService.PREFIX}{identifier}"
            await client.delete(valkey_key)
        except Exception:
            return

    @staticmethod
    @valkey_operation
    async def is_locked(client, identifier: str) -> bool:
        try:
            valkey_key = f"{LoginAttemptService.PREFIX}{identifier}"
            count = await client.get(valkey_key)
            return int(count) >= settings.LOGIN_MAX_ATTEMPTS if count else False
        except Exception:
            return False
