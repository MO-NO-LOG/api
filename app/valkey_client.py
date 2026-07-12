from valkey.asyncio import Valkey

from app.config import settings

_valkey: Valkey | None = None


def get_valkey_client() -> Valkey:
    global _valkey
    if _valkey is None:
        _valkey = Valkey(
            host=settings.VALKEY_HOST,
            port=settings.VALKEY_PORT,
            db=settings.VALKEY_DB,
            password=settings.VALKEY_PASSWORD if settings.VALKEY_PASSWORD else None,
            decode_responses=True,
        )
    return _valkey


async def close_valkey() -> None:
    global _valkey
    if _valkey is not None:
        await _valkey.aclose()
        _valkey = None
