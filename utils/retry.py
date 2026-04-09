from __future__ import annotations

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")

LOGGER = logging.getLogger(__name__)


def retry(
    attempts: int = 3,
    delay_seconds: float = 1.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Retry transient operations with a small fixed delay."""

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # pragma: no cover - defensive
                    last_error = exc
                    LOGGER.warning(
                        "Retryable error in %s (attempt %s/%s): %s",
                        func.__name__,
                        attempt,
                        attempts,
                        exc,
                    )
                    if attempt < attempts:
                        time.sleep(delay_seconds)
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator
