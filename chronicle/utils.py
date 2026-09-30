"""Retry utilities with exponential backoff."""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import time
from typing import Any, Awaitable, Callable, TypeVar, cast

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Retry decorator with exponential backoff for sync and async functions."""

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                delay = initial_delay
                last_exception: Exception | None = None

                for attempt in range(max_retries + 1):
                    try:
                        async_func = cast(Callable[..., Awaitable[Any]], func)
                        return await async_func(*args, **kwargs)
                    except exceptions as exc:
                        last_exception = exc
                        if attempt == max_retries:
                            logger.error(
                                "%s failed after %s retries",
                                func.__name__,
                                max_retries,
                                exc_info=True,
                            )
                            raise

                        logger.warning(
                            "%s failed (attempt %s/%s), retrying in %.1fs: %s",
                            func.__name__,
                            attempt + 1,
                            max_retries + 1,
                            delay,
                            exc,
                        )
                        await asyncio.sleep(delay)
                        delay = min(delay * exponential_base, max_delay)

                raise RuntimeError(
                    f"Retry loop exited unexpectedly for async function {func.__name__}"
                ) from last_exception

            return cast(F, async_wrapper)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    sync_func = cast(Callable[..., Any], func)
                    return sync_func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc

                    if attempt == max_retries:
                        logger.error(
                            "%s failed after %s retries",
                            func.__name__,
                            max_retries,
                            exc_info=True,
                        )
                        raise

                    logger.warning(
                        "%s failed (attempt %s/%s), retrying in %.1fs: %s",
                        func.__name__,
                        attempt + 1,
                        max_retries + 1,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)

            raise RuntimeError(
                f"Retry loop exited unexpectedly for sync function {func.__name__}"
            ) from last_exception

        return cast(F, sync_wrapper)

    return decorator
