from app.config import settings
from app.valkey_client import get_valkey_client


class RateLimitService:
    PREFIX = "rl:"

    @staticmethod
    async def allow(key: str, max_requests: int, window_seconds: int) -> bool:
        try:
            client = get_valkey_client()
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
    async def register_failure(identifier: str) -> int:
        try:
            client = get_valkey_client()
            valkey_key = f"{LoginAttemptService.PREFIX}{identifier}"
            count = await client.incr(valkey_key)
            if count == 1:
                await client.expire(valkey_key, settings.LOGIN_ATTEMPT_WINDOW_SECONDS)
            return int(count)
        except Exception:
            return 0

    @staticmethod
    async def reset(identifier: str) -> None:
        try:
            client = get_valkey_client()
            valkey_key = f"{LoginAttemptService.PREFIX}{identifier}"
            await client.delete(valkey_key)
        except Exception:
            return

    @staticmethod
    async def is_locked(identifier: str) -> bool:
        try:
            client = get_valkey_client()
            valkey_key = f"{LoginAttemptService.PREFIX}{identifier}"
            count = await client.get(valkey_key)
            return int(count) >= settings.LOGIN_MAX_ATTEMPTS if count else False
        except Exception:
            return False
