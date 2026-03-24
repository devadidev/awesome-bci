"""Circuit breaker pattern for resilient external data source calls."""
import asyncio
import time
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass, field
from src.logger import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing - reject calls immediately
    HALF_OPEN = "half_open" # Testing if service recovered


class CircuitOpenError(Exception):
    """Raised when circuit is open and call is rejected."""
    def __init__(self, name: str, retry_after: float):
        self.name = name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit '{name}' is OPEN. Retry after {retry_after:.1f}s"
        )


@dataclass
class CircuitStats:
    failures: int = 0
    successes: int = 0
    rejected: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changed_at: float = field(default_factory=time.monotonic)


class CircuitBreaker:
    """
    Circuit breaker for protecting external API/data-source calls.

    States:
      CLOSED   -> normal; failures increment counter
      OPEN     -> tripped; calls rejected until timeout
      HALF_OPEN -> one probe call allowed; success resets, failure re-opens
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def stats(self) -> CircuitStats:
        return self._stats

    def _retry_after(self) -> float:
        if self._stats.last_failure_time is None:
            return 0.0
        elapsed = time.monotonic() - self._stats.last_failure_time
        return max(0.0, self.recovery_timeout - elapsed)

    async def _transition(self, new_state: CircuitState) -> None:
        old_state = self._state
        self._state = new_state
        self._stats.state_changed_at = time.monotonic()
        logger.info(
            "circuit_state_change",
            circuit=self.name,
            from_state=old_state,
            to_state=new_state,
        )

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        async with self._lock:
            if self._state == CircuitState.OPEN:
                retry_after = self._retry_after()
                if retry_after > 0:
                    self._stats.rejected += 1
                    raise CircuitOpenError(self.name, retry_after)
                # Timeout expired - transition to HALF_OPEN
                await self._transition(CircuitState.HALF_OPEN)
                self._half_open_calls = 0

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    self._stats.rejected += 1
                    raise CircuitOpenError(self.name, self._retry_after())
                self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as exc:
            await self._on_failure(exc)
            raise

    async def _on_success(self) -> None:
        async with self._lock:
            self._stats.successes += 1
            self._stats.last_success_time = time.monotonic()
            if self._state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                self._stats.failures = 0
                await self._transition(CircuitState.CLOSED)

    async def _on_failure(self, exc: Exception) -> None:
        async with self._lock:
            self._stats.failures += 1
            self._stats.last_failure_time = time.monotonic()
            logger.warning(
                "circuit_failure",
                circuit=self.name,
                failures=self._stats.failures,
                threshold=self.failure_threshold,
                error=str(exc),
            )
            if self._state == CircuitState.HALF_OPEN:
                await self._transition(CircuitState.OPEN)
            elif (
                self._state == CircuitState.CLOSED
                and self._stats.failures >= self.failure_threshold
            ):
                await self._transition(CircuitState.OPEN)

    def reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_calls = 0
        logger.info("circuit_reset", circuit=self.name)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self._state,
            "failures": self._stats.failures,
            "successes": self._stats.successes,
            "rejected": self._stats.rejected,
            "retry_after_seconds": self._retry_after() if self._state == CircuitState.OPEN else 0,
        }
