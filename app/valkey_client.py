from valkey.asyncio import Valkey

from app.config import settings


def get_valkey_client() -> Valkey:
    """
    Create and return a new async Valkey client instance.

    Returns:
        Async Valkey client instance
    """
    return Valkey(
        host=settings.VALKEY_HOST,
        port=settings.VALKEY_PORT,
        db=settings.VALKEY_DB,
        password=settings.VALKEY_PASSWORD if settings.VALKEY_PASSWORD else None,
        decode_responses=True,  # Automatically decode responses to strings
    )
