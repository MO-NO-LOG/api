from datetime import timedelta
from app.redis_client import get_redis_client
from app.config import settings


class RateLimitService:
    PREFIX = "rl:"

    @staticmethod
    async def allow(key: str, max_requests: int, window_seconds: int) -> bool:
        redis_client = None
        try:
            redis_client = get_redis_client()
            redis_key = f"{RateLimitService.PREFIX}{key}"
            count = await redis_client.incr(redis_key)
            if count == 1:
                await redis_client.expire(redis_key, window_seconds)
            return count <= max_requests
        except Exception:
            return True
        finally:
            if redis_client:
                await redis_client.aclose()


class LoginAttemptService:
    PREFIX = "login_attempts:"

    @staticmethod
    async def register_failure(identifier: str) -> int:
        redis_client = None
        try:
            redis_client = get_redis_client()
            redis_key = f"{LoginAttemptService.PREFIX}{identifier}"
            count = await redis_client.incr(redis_key)
            if count == 1:
                await redis_client.expire(
                    redis_key, settings.LOGIN_ATTEMPT_WINDOW_SECONDS
                )
            return int(count)
        except Exception:
            return 0
        finally:
            if redis_client:
                await redis_client.aclose()

    @staticmethod
    async def reset(identifier: str) -> None:
        redis_client = None
        try:
            redis_client = get_redis_client()
            redis_key = f"{LoginAttemptService.PREFIX}{identifier}"
            await redis_client.delete(redis_key)
        except Exception:
            return
        finally:
            if redis_client:
                await redis_client.aclose()

    @staticmethod
    async def is_locked(identifier: str) -> bool:
        redis_client = None
        try:
            redis_client = get_redis_client()
            redis_key = f"{LoginAttemptService.PREFIX}{identifier}"
            count = await redis_client.get(redis_key)
            return int(count) >= settings.LOGIN_MAX_ATTEMPTS if count else False
        except Exception:
            return False
        finally:
            if redis_client:
                await redis_client.aclose()
