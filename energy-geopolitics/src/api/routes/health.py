"""Health check and system status routes."""
from fastapi import APIRouter
from src.data.db import get_store
from src.logger import get_logger

router = APIRouter(prefix="/health", tags=["Health"])
logger = get_logger(__name__)

# Recovery manager injected at startup
_recovery_manager = None


def set_recovery_manager(rm):
    global _recovery_manager
    _recovery_manager = rm


@router.get("/")
async def health_check():
    store = get_store()
    return {
        "status": "healthy",
        "store": store.stats(),
    }


@router.get("/recovery")
async def recovery_status():
    """Get recovery stack status: circuit breakers and collector health."""
    if _recovery_manager is None:
        return {"status": "recovery_manager_not_initialized"}
    return _recovery_manager.system_status()


@router.get("/recovery/collectors")
async def collector_health():
    if _recovery_manager is None:
        return []
    return [
        {
            "collector_id": h.collector_id,
            "healthy": h.healthy,
            "circuit_state": h.circuit_state,
            "consecutive_failures": h.consecutive_failures,
            "last_success": h.last_success,
        }
        for h in _recovery_manager.health_summary()
    ]


@router.post("/recovery/reset/{circuit_name}")
async def reset_circuit(circuit_name: str):
    """Manually reset an open circuit breaker."""
    if _recovery_manager is None:
        return {"success": False, "reason": "recovery_manager_not_initialized"}
    success = _recovery_manager.reset_circuit(circuit_name)
    return {"success": success, "circuit": circuit_name}
