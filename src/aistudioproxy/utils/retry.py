# -*- coding: utf-8 -*-
"""
Retry mechanism for AIStudioProxy.

This module provides a decorator for retrying operations with exponential backoff.
"""

import asyncio
import random
from functools import wraps
from typing import Any, Callable, Coroutine

from .logger import get_logger

logger = get_logger(__name__)


def async_retry(
    attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    factor: float = 2.0,
    jitter: float = 0.1,
):
    """
    A decorator for retrying an async function with exponential backoff.

    Args:
        attempts: The maximum number of attempts.
        initial_delay: The initial delay in seconds.
        max_delay: The maximum delay in seconds.
        factor: The factor by which to multiply the delay for each attempt.
        jitter: The amount of jitter to add to the delay.
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            for attempt in range(1, attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == attempts:
                        logger.error(
                            "Function failed after max attempts",
                            func_name=func.__name__,
                            attempt=attempt,
                            error=str(e),
                        )
                        raise

                    logger.warning(
                        "Attempt failed, retrying...",
                        func_name=func.__name__,
                        attempt=attempt,
                        delay=delay,
                        error=str(e),
                    )

                    # Apply jitter
                    jittered_delay = delay + random.uniform(-jitter, jitter) * delay
                    await asyncio.sleep(jittered_delay)

                    # Exponential backoff
                    delay = min(delay * factor, max_delay)

        return wrapper

    return decorator
