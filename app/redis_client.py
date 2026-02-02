from redis.asyncio import Redis

from app.config import settings


def get_redis_client() -> Redis:
    """
    Create and return a new async Redis client instance.

    Returns:
        Async Redis client instance
    """
    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
        decode_responses=True,  # Automatically decode responses to strings
    )
