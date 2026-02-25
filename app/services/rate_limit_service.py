from datetime import timedelta

from app.config import settings
from app.valkey_client import get_valkey_client


class RateLimitService:
    PREFIX = "rl:"

    @staticmethod
    async def allow(key: str, max_requests: int, window_seconds: int) -> bool:
        valkey_client = None
        try:
            valkey_client = get_valkey_client()
            valkey_key = f"{RateLimitService.PREFIX}{key}"
            count = await valkey_client.incr(valkey_key)
            if count == 1:
                await valkey_client.expire(valkey_key, window_seconds)
            return count <= max_requests
        except Exception:
            return True
        finally:
            if valkey_client:
                await valkey_client.aclose()


class LoginAttemptService:
    PREFIX = "login_attempts:"

    @staticmethod
    async def register_failure(identifier: str) -> int:
        valkey_client = None
        try:
            valkey_client = get_valkey_client()
            valkey_key = f"{LoginAttemptService.PREFIX}{identifier}"
            count = await valkey_client.incr(valkey_key)
            if count == 1:
                await valkey_client.expire(
                    valkey_key, settings.LOGIN_ATTEMPT_WINDOW_SECONDS
                )
            return int(count)
        except Exception:
            return 0
        finally:
            if valkey_client:
                await valkey_client.aclose()

    @staticmethod
    async def reset(identifier: str) -> None:
        valkey_client = None
        try:
            valkey_client = get_valkey_client()
            valkey_key = f"{LoginAttemptService.PREFIX}{identifier}"
            await valkey_client.delete(valkey_key)
        except Exception:
            return
        finally:
            if valkey_client:
                await valkey_client.aclose()

    @staticmethod
    async def is_locked(identifier: str) -> bool:
        valkey_client = None
        try:
            valkey_client = get_valkey_client()
            valkey_key = f"{LoginAttemptService.PREFIX}{identifier}"
            count = await valkey_client.get(valkey_key)
            return int(count) >= settings.LOGIN_MAX_ATTEMPTS if count else False
        except Exception:
            return False
        finally:
            if valkey_client:
                await valkey_client.aclose()
