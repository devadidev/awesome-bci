"""Sanctions data collector - monitors OFAC, EU, and UN sanctions lists."""
from datetime import datetime
from typing import Any, List
from src.collectors.base import BaseCollector
from src.data.db import get_store
from src.models import GeopoliticalEvent, EventType, EventSeverity, EventStatus
from src.recovery import RecoveryManager
from src.logger import get_logger

logger = get_logger(__name__)

KNOWN_SANCTIONED_ENTITIES = [
    {
        "entity": "Rosneft",
        "country": "Russia",
        "region": "Eastern Europe",
        "sanctioning_body": "EU / UK",
        "supply_impact_bpd": 4000000,
        "tags": ["Russia", "Rosneft", "EU sanctions", "OFAC"],
    },
    {
        "entity": "National Iranian Oil Company (NIOC)",
        "country": "Iran",
        "region": "Middle East",
        "sanctioning_body": "US OFAC",
        "supply_impact_bpd": 1500000,
        "tags": ["Iran", "NIOC", "OFAC", "nuclear"],
    },
    {
        "entity": "Syrian Petroleum Company",
        "country": "Syria",
        "region": "Middle East",
        "sanctioning_body": "US / EU",
        "supply_impact_bpd": 25000,
        "tags": ["Syria", "sanctions", "SPC"],
    },
    {
        "entity": "PDVSA (Venezuela)",
        "country": "Venezuela",
        "region": "Latin America",
        "sanctioning_body": "US OFAC",
        "supply_impact_bpd": 800000,
        "tags": ["Venezuela", "PDVSA", "OFAC", "Maduro"],
    },
]


class SanctionsCollector(BaseCollector):
    """
    Monitors sanctions lists for oil and gas entities.

    In production: integrates with OFAC SDN list API, EU sanctions API.
    For MVP: uses curated static dataset, refreshed periodically.
    """

    def __init__(self, recovery_manager: RecoveryManager, interval_seconds: int = 3600):
        super().__init__("sanctions_collector", recovery_manager, interval_seconds)
        self._loaded = False

    async def _fetch(self) -> List[dict]:
        if self._loaded:
            return []  # Only load once per run
        logger.info("sanctions_fetch", source="static_dataset")
        return KNOWN_SANCTIONED_ENTITIES

    async def _process(self, raw_items: List[Any]) -> int:
        store = get_store()
        count = 0
        for item in raw_items:
            title = f"Active Sanctions: {item['entity']}"
            existing = store.filter("events", title=title)
            if existing:
                continue
            event = GeopoliticalEvent(
                title=title,
                description=(
                    f"{item['entity']} remains under active sanctions imposed by "
                    f"{item['sanctioning_body']}. Energy exports severely restricted."
                ),
                event_type=EventType.SANCTIONS,
                severity=EventSeverity.HIGH,
                status=EventStatus.ACTIVE,
                country=item["country"],
                region=item["region"],
                supply_impact_bpd=item.get("supply_impact_bpd"),
                source="sanctions_database",
                tags=item.get("tags", []),
                confidence_score=0.99,
            )
            store.insert("events", event.model_dump())
            count += 1
        self._loaded = True
        return count
