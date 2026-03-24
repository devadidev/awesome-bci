"""Base collector with integrated recovery stack."""
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, List, Optional
from src.logger import get_logger
from src.recovery import RecoveryManager, RetryConfig

logger = get_logger(__name__)


class BaseCollector(ABC):
    """
    Abstract base for all data collectors.

    Subclasses implement `_fetch()` to retrieve raw data.
    The base class handles:
      - Circuit breaker protection
      - Exponential backoff retry
      - Checkpoint save/load for resume-on-failure
    """

    def __init__(
        self,
        collector_id: str,
        recovery_manager: RecoveryManager,
        interval_seconds: int = 300,
    ):
        self.collector_id = collector_id
        self._recovery = recovery_manager
        self._interval = interval_seconds
        self._cb = recovery_manager.get_circuit_breaker(collector_id)
        self._retry_config = recovery_manager.retry_config
        self._running = False
        self._task: Optional[asyncio.Task] = None

    @abstractmethod
    async def _fetch(self) -> List[Any]:
        """Fetch raw data from external source. Must be implemented by subclass."""
        ...

    @abstractmethod
    async def _process(self, raw_items: List[Any]) -> int:
        """Process and persist fetched items. Returns count of items ingested."""
        ...

    async def run_once(self) -> int:
        """Run a single collection cycle with full recovery protection."""
        checkpoint = self._recovery.checkpoint_manager.load(self.collector_id)
        cursor = checkpoint.cursor if checkpoint else None

        try:
            logger.info("collector_run_start", collector=self.collector_id, cursor=cursor)

            raw = await self._cb.call(self._fetch)
            count = await self._process(raw)

            self._recovery.checkpoint_manager.mark_success(
                self.collector_id,
                items_processed=count,
                cursor=datetime.utcnow().isoformat(),
            )
            logger.info("collector_run_complete", collector=self.collector_id, items=count)
            return count

        except Exception as exc:
            self._recovery.checkpoint_manager.mark_failure(
                self.collector_id,
                error=str(exc),
                cursor=cursor,
            )
            logger.error("collector_run_failed", collector=self.collector_id, error=str(exc))
            raise

    async def start(self) -> None:
        """Start the collector loop in the background."""
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("collector_started", collector=self.collector_id, interval=self._interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("collector_stopped", collector=self.collector_id)

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.run_once()
            except Exception:
                pass  # Errors already logged; circuit breaker handles back-off
            await asyncio.sleep(self._interval)
