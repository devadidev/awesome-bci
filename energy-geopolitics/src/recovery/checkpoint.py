"""Checkpointing for collector state recovery after failures."""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Checkpoint:
    collector_id: str
    last_run_at: str
    last_success_at: Optional[str]
    items_processed: int
    cursor: Optional[str]          # pagination cursor / timestamp marker
    metadata: Dict[str, Any]
    failed: bool = False
    error: Optional[str] = None


class CheckpointManager:
    """
    Persists collector progress to disk so data ingestion can resume
    from where it left off after crashes or restarts.
    """

    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        self._dir = Path(checkpoint_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        logger.info("checkpoint_manager_init", directory=str(self._dir))

    def _path(self, collector_id: str) -> Path:
        safe_id = collector_id.replace("/", "_").replace(" ", "_")
        return self._dir / f"{safe_id}.json"

    def save(self, checkpoint: Checkpoint) -> None:
        path = self._path(checkpoint.collector_id)
        try:
            with open(path, "w") as f:
                json.dump(asdict(checkpoint), f, indent=2)
            logger.debug("checkpoint_saved", collector=checkpoint.collector_id)
        except OSError as exc:
            logger.error("checkpoint_save_failed", collector=checkpoint.collector_id, error=str(exc))

    def load(self, collector_id: str) -> Optional[Checkpoint]:
        path = self._path(collector_id)
        if not path.exists():
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            return Checkpoint(**data)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            logger.error("checkpoint_load_failed", collector=collector_id, error=str(exc))
            return None

    def mark_success(
        self,
        collector_id: str,
        items_processed: int,
        cursor: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Checkpoint:
        now = datetime.utcnow().isoformat()
        cp = Checkpoint(
            collector_id=collector_id,
            last_run_at=now,
            last_success_at=now,
            items_processed=items_processed,
            cursor=cursor,
            metadata=metadata or {},
            failed=False,
        )
        self.save(cp)
        return cp

    def mark_failure(
        self,
        collector_id: str,
        error: str,
        items_processed: int = 0,
        cursor: Optional[str] = None,
    ) -> Checkpoint:
        existing = self.load(collector_id)
        now = datetime.utcnow().isoformat()
        cp = Checkpoint(
            collector_id=collector_id,
            last_run_at=now,
            last_success_at=existing.last_success_at if existing else None,
            items_processed=items_processed,
            cursor=cursor or (existing.cursor if existing else None),
            metadata=existing.metadata if existing else {},
            failed=True,
            error=error,
        )
        self.save(cp)
        return cp

    def list_all(self) -> Dict[str, Optional[Checkpoint]]:
        result = {}
        for path in self._dir.glob("*.json"):
            collector_id = path.stem
            result[collector_id] = self.load(collector_id)
        return result

    def delete(self, collector_id: str) -> None:
        path = self._path(collector_id)
        if path.exists():
            path.unlink()
            logger.info("checkpoint_deleted", collector=collector_id)
