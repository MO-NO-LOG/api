from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, AsyncGenerator, Callable, TypeVar

from valkey.asyncio import Valkey

from app.valkey_client import get_valkey_client

F = TypeVar("F", bound=Callable[..., Any])


@asynccontextmanager
async def valkey_client() -> AsyncGenerator[Valkey, None]:
    """Async context manager that yields a Valkey client and closes it."""
    client = get_valkey_client()
    try:
        yield client
    finally:
        await client.aclose()


def valkey_operation(func: F) -> F:
    """Decorator that injects a Valkey client as the first positional argument."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        async with valkey_client() as client:
            return await func(client, *args, **kwargs)

    return wrapper  # type: ignore[return-value]
