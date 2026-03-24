"""Orchestrates the full recovery stack: circuit breakers, retries, checkpoints."""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from src.logger import get_logger
from .circuit_breaker import CircuitBreaker
from .retry import RetryConfig
from .checkpoint import CheckpointManager, Checkpoint

logger = get_logger(__name__)


@dataclass
class CollectorHealth:
    collector_id: str
    healthy: bool
    circuit_state: str
    last_success: Optional[str]
    last_failure: Optional[str]
    consecutive_failures: int
    checkpoint: Optional[Checkpoint] = None


class RecoveryManager:
    """
    Central recovery coordinator.

    Provides:
    - Circuit breaker registry (one per external data source)
    - Shared checkpoint manager
    - Shared retry configuration
    - Health summary across all collectors
    """

    def __init__(
        self,
        checkpoint_dir: str = "./checkpoints",
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        retry_max_attempts: int = 3,
        retry_base_delay: float = 2.0,
    ):
        self._checkpoint_manager = CheckpointManager(checkpoint_dir)
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._retry_config = RetryConfig(
            max_attempts=retry_max_attempts,
            base_delay=retry_base_delay,
        )
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._failure_counts: Dict[str, int] = {}
        logger.info("recovery_manager_init")

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a named data source."""
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=self._failure_threshold,
                recovery_timeout=self._recovery_timeout,
            )
            logger.info("circuit_breaker_created", name=name)
        return self._circuit_breakers[name]

    @property
    def retry_config(self) -> RetryConfig:
        return self._retry_config

    @property
    def checkpoint_manager(self) -> CheckpointManager:
        return self._checkpoint_manager

    def health_summary(self) -> List[CollectorHealth]:
        checkpoints = self._checkpoint_manager.list_all()
        health = []

        all_ids = set(self._circuit_breakers.keys()) | set(checkpoints.keys())

        for cid in sorted(all_ids):
            cb = self._circuit_breakers.get(cid)
            cp = checkpoints.get(cid)
            health.append(
                CollectorHealth(
                    collector_id=cid,
                    healthy=cb is None or cb.state.value == "closed",
                    circuit_state=cb.state.value if cb else "no_circuit",
                    last_success=cp.last_success_at if cp else None,
                    last_failure=cp.error if cp and cp.failed else None,
                    consecutive_failures=cb.stats.failures if cb else 0,
                    checkpoint=cp,
                )
            )
        return health

    def reset_circuit(self, name: str) -> bool:
        cb = self._circuit_breakers.get(name)
        if cb:
            cb.reset()
            return True
        return False

    def system_status(self) -> dict:
        health = self.health_summary()
        open_circuits = [h for h in health if h.circuit_state == "open"]
        degraded = [h for h in health if h.circuit_state == "half_open"]
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_collectors": len(health),
            "healthy": len([h for h in health if h.healthy]),
            "open_circuits": len(open_circuits),
            "degraded": len(degraded),
            "collectors": [
                {
                    "id": h.collector_id,
                    "healthy": h.healthy,
                    "circuit_state": h.circuit_state,
                    "consecutive_failures": h.consecutive_failures,
                    "last_success": h.last_success,
                }
                for h in health
            ],
        }
