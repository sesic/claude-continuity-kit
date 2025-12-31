"""
Retry decorator for handling transient failures.

This module provides a decorator that automatically retries a function
when it raises an exception, with configurable attempts and delay.
"""

import asyncio
import functools
import logging
import time
from typing import TypeVar, ParamSpec, Callable, Awaitable

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator that retries a function on failure.

    Args:
        max_attempts: Maximum number of attempts before giving up (default: 3)
        delay: Seconds to wait between retries (default: 1.0)

    Returns:
        Decorated function that will retry on exception

    Raises:
        The last exception encountered if all attempts fail

    Example:
        @retry(max_attempts=3, delay=0.5)
        def flaky_api_call():
            response = requests.get("https://api.example.com")
            response.raise_for_status()
            return response.json()

        @retry(max_attempts=5, delay=2.0)
        async def async_flaky_call():
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.example.com") as resp:
                    return await resp.json()
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                last_exception: BaseException | None = None

                for attempt in range(1, max_attempts + 1):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_attempts:
                            logger.warning(
                                "Attempt %d/%d failed for %s: %s. "
                                "Retrying in %.1f seconds...",
                                attempt,
                                max_attempts,
                                func.__name__,
                                str(e),
                                delay,
                            )
                            await asyncio.sleep(delay)
                        else:
                            logger.warning(
                                "Attempt %d/%d failed for %s: %s. "
                                "No more retries.",
                                attempt,
                                max_attempts,
                                func.__name__,
                                str(e),
                            )

                assert last_exception is not None
                raise last_exception

            return async_wrapper  # type: ignore[return-value]
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                last_exception: BaseException | None = None

                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_attempts:
                            logger.warning(
                                "Attempt %d/%d failed for %s: %s. "
                                "Retrying in %.1f seconds...",
                                attempt,
                                max_attempts,
                                func.__name__,
                                str(e),
                                delay,
                            )
                            time.sleep(delay)
                        else:
                            logger.warning(
                                "Attempt %d/%d failed for %s: %s. "
                                "No more retries.",
                                attempt,
                                max_attempts,
                                func.__name__,
                                str(e),
                            )

                assert last_exception is not None
                raise last_exception

            return sync_wrapper  # type: ignore[return-value]

    return decorator
