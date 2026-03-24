"""Retry with exponential backoff and jitter."""
import asyncio
import random
import time
from dataclasses import dataclass
from typing import Callable, Any, Tuple, Type
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 2.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)

    def delay_for(self, attempt: int) -> float:
        """Calculate delay for the given attempt (0-indexed)."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay,
        )
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay


async def retry_with_backoff(
    func: Callable,
    *args: Any,
    config: RetryConfig = None,
    operation_name: str = "operation",
    **kwargs: Any,
) -> Any:
    """
    Execute an async callable with exponential backoff retry.

    Retries on any exception in config.retryable_exceptions up to
    config.max_attempts times.
    """
    cfg = config or RetryConfig()
    last_exc: Exception = RuntimeError("No attempts made")

    for attempt in range(cfg.max_attempts):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            if attempt > 0:
                logger.info(
                    "retry_succeeded",
                    operation=operation_name,
                    attempt=attempt + 1,
                )
            return result
        except cfg.retryable_exceptions as exc:
            last_exc = exc
            if attempt + 1 >= cfg.max_attempts:
                logger.error(
                    "retry_exhausted",
                    operation=operation_name,
                    attempts=cfg.max_attempts,
                    error=str(exc),
                )
                break

            delay = cfg.delay_for(attempt)
            logger.warning(
                "retry_attempt",
                operation=operation_name,
                attempt=attempt + 1,
                max_attempts=cfg.max_attempts,
                delay=round(delay, 2),
                error=str(exc),
            )
            await asyncio.sleep(delay)

    raise last_exc


class RetryableCollector:
    """Mixin that adds retry + circuit breaker to data collectors."""

    def __init__(self, circuit_breaker=None, retry_config: RetryConfig = None):
        self._circuit_breaker = circuit_breaker
        self._retry_config = retry_config or RetryConfig()

    async def fetch_with_resilience(
        self, func: Callable, *args, operation: str = "fetch", **kwargs
    ) -> Any:
        async def _call():
            if self._circuit_breaker:
                return await self._circuit_breaker.call(func, *args, **kwargs)
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

        return await retry_with_backoff(
            _call,
            config=self._retry_config,
            operation_name=operation,
        )
