"""Tests for the recovery stack: circuit breaker, retry, checkpoint."""
import asyncio
import pytest
import tempfile
import os
from src.recovery.circuit_breaker import CircuitBreaker, CircuitState, CircuitOpenError
from src.recovery.retry import RetryConfig, retry_with_backoff
from src.recovery.checkpoint import CheckpointManager, Checkpoint
from src.recovery.recovery_manager import RecoveryManager


# ── Circuit Breaker ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_circuit_starts_closed():
    cb = CircuitBreaker("test-cb", failure_threshold=3)
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_succeeds_when_closed():
    cb = CircuitBreaker("test-cb", failure_threshold=3)

    async def returns_42():
        return 42

    result = await cb.call(returns_42)
    assert result == 42


@pytest.mark.asyncio
async def test_circuit_opens_after_threshold():
    cb = CircuitBreaker("test-cb-open", failure_threshold=3, recovery_timeout=100)

    async def failing():
        raise ValueError("simulated failure")

    for _ in range(3):
        with pytest.raises(ValueError):
            await cb.call(failing)

    assert cb.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_rejects_when_open():
    cb = CircuitBreaker("test-cb-reject", failure_threshold=2, recovery_timeout=100)

    async def failing():
        raise ConnectionError("down")

    for _ in range(2):
        with pytest.raises(ConnectionError):
            await cb.call(failing)

    assert cb.state == CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        await cb.call(failing)
    assert cb.stats.rejected >= 1


@pytest.mark.asyncio
async def test_circuit_reset():
    cb = CircuitBreaker("test-cb-reset", failure_threshold=2, recovery_timeout=100)

    async def failing():
        raise ValueError("fail")

    for _ in range(2):
        with pytest.raises(ValueError):
            await cb.call(failing)

    assert cb.state == CircuitState.OPEN
    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.stats.failures == 0


# ── Retry ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retry_succeeds_first_attempt():
    calls = []

    async def ok():
        calls.append(1)
        return "success"

    result = await retry_with_backoff(ok, config=RetryConfig(max_attempts=3, base_delay=0.01))
    assert result == "success"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_retry_succeeds_after_failures():
    calls = []

    async def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("not yet")
        return "ok"

    result = await retry_with_backoff(
        flaky,
        config=RetryConfig(max_attempts=3, base_delay=0.01, jitter=False),
    )
    assert result == "ok"
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_retry_exhausted_raises():
    async def always_fails():
        raise RuntimeError("always fails")

    with pytest.raises(RuntimeError, match="always fails"):
        await retry_with_backoff(
            always_fails,
            config=RetryConfig(max_attempts=3, base_delay=0.01, jitter=False),
        )


# ── Checkpoint ────────────────────────────────────────────────────────────────

def test_checkpoint_save_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = CheckpointManager(tmpdir)
        cp = mgr.mark_success(
            "test_collector",
            items_processed=42,
            cursor="2024-01-01T00:00:00",
            metadata={"region": "global"},
        )
        assert cp.items_processed == 42
        assert not cp.failed

        loaded = mgr.load("test_collector")
        assert loaded is not None
        assert loaded.items_processed == 42
        assert loaded.cursor == "2024-01-01T00:00:00"
        assert loaded.metadata["region"] == "global"


def test_checkpoint_failure_preserves_cursor():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = CheckpointManager(tmpdir)
        mgr.mark_success("test_c", items_processed=10, cursor="cursor-1")
        mgr.mark_failure("test_c", error="Connection reset", items_processed=0)

        loaded = mgr.load("test_c")
        assert loaded.failed
        assert loaded.cursor == "cursor-1"  # Preserved from last success
        assert "Connection reset" in loaded.error


def test_checkpoint_nonexistent_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = CheckpointManager(tmpdir)
        assert mgr.load("nonexistent") is None


def test_checkpoint_list_all():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = CheckpointManager(tmpdir)
        mgr.mark_success("c1", items_processed=1)
        mgr.mark_success("c2", items_processed=2)
        result = mgr.list_all()
        assert "c1" in result
        assert "c2" in result


# ── Recovery Manager ──────────────────────────────────────────────────────────

def test_recovery_manager_creates_circuit_breakers():
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = RecoveryManager(checkpoint_dir=tmpdir)
        cb1 = rm.get_circuit_breaker("source-a")
        cb2 = rm.get_circuit_breaker("source-b")
        cb3 = rm.get_circuit_breaker("source-a")  # Same as cb1
        assert cb1 is cb3
        assert cb1 is not cb2


def test_recovery_manager_system_status():
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = RecoveryManager(checkpoint_dir=tmpdir)
        rm.get_circuit_breaker("test-src")
        status = rm.system_status()
        assert "timestamp" in status
        assert "total_collectors" in status
        assert status["total_collectors"] >= 1
