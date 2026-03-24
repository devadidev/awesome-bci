"""Database setup with SQLAlchemy async engine and in-memory store for MVP."""
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from src.logger import get_logger

logger = get_logger(__name__)


class InMemoryStore:
    """
    Lightweight in-memory data store for MVP.
    Keyed by collection name -> dict[id, record].
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {
            "events": {},
            "assets": {},
            "risks": {},
            "intelligence": {},
            "alerts": {},
            "prices": [],
        }

    # ── Generic CRUD ──────────────────────────────────────────────────────────

    def insert(self, collection: str, record: dict) -> dict:
        self._store.setdefault(collection, {})
        rid = record.get("id")
        if not rid:
            raise ValueError(f"Record missing 'id' field: {record}")
        self._store[collection][rid] = record
        return record

    def get(self, collection: str, record_id: str) -> Optional[dict]:
        return self._store.get(collection, {}).get(record_id)

    def list_all(self, collection: str) -> List[dict]:
        return list(self._store.get(collection, {}).values())

    def update(self, collection: str, record_id: str, updates: dict) -> Optional[dict]:
        record = self.get(collection, record_id)
        if record is None:
            return None
        record.update({k: v for k, v in updates.items() if v is not None})
        record["updated_at"] = datetime.utcnow().isoformat()
        self._store[collection][record_id] = record
        return record

    def delete(self, collection: str, record_id: str) -> bool:
        if record_id in self._store.get(collection, {}):
            del self._store[collection][record_id]
            return True
        return False

    def filter(self, collection: str, **filters) -> List[dict]:
        records = self.list_all(collection)
        for key, value in filters.items():
            if value is not None:
                records = [r for r in records if r.get(key) == value]
        return records

    # ── Price time series ─────────────────────────────────────────────────────

    def append_price(self, snapshot: dict) -> None:
        self._store["prices"].append(snapshot)
        # Keep only last 1000 snapshots
        if len(self._store["prices"]) > 1000:
            self._store["prices"] = self._store["prices"][-1000:]

    def latest_price(self) -> Optional[dict]:
        prices = self._store["prices"]
        return prices[-1] if prices else None

    def price_history(self, limit: int = 100) -> List[dict]:
        return self._store["prices"][-limit:]

    def stats(self) -> dict:
        return {
            col: len(records) if isinstance(records, (dict, list)) else 0
            for col, records in self._store.items()
        }


# Singleton store instance
_store: Optional[InMemoryStore] = None


def get_store() -> InMemoryStore:
    global _store
    if _store is None:
        _store = InMemoryStore()
    return _store
