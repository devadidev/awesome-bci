"""Geopolitical news collector for oil and gas event detection."""
import random
from datetime import datetime, timedelta
from typing import Any, List
import httpx
from src.collectors.base import BaseCollector
from src.data.db import get_store
from src.models import GeopoliticalEvent, EventType, EventSeverity, EventStatus
from src.recovery import RecoveryManager
from src.logger import get_logger

logger = get_logger(__name__)

# Keywords that indicate energy geopolitical relevance
ENERGY_KEYWORDS = [
    "oil", "crude", "pipeline", "refinery", "OPEC", "LNG", "gas",
    "sanctions", "energy", "petroleum", "tanker", "Aramco",
]

SIMULATED_NEWS_TEMPLATES = [
    {
        "title": "Kazakhstan Caspian Pipeline Consortium Reports Maintenance Shutdown",
        "event_type": EventType.PIPELINE_INCIDENT,
        "severity": EventSeverity.MODERATE,
        "country": "Kazakhstan",
        "region": "Central Asia",
        "supply_impact_bpd": 120000,
        "tags": ["Kazakhstan", "CPC", "Caspian", "maintenance"],
    },
    {
        "title": "Nigeria NNPC Reports Force Majeure on Bonny Light Exports",
        "event_type": EventType.SUPPLY_DISRUPTION,
        "severity": EventSeverity.HIGH,
        "country": "Nigeria",
        "region": "West Africa",
        "supply_impact_bpd": 250000,
        "tags": ["Nigeria", "NNPC", "Bonny Light", "force majeure"],
    },
    {
        "title": "G7 Nations Announce Tightened Russian Oil Price Cap Enforcement",
        "event_type": EventType.SANCTIONS,
        "severity": EventSeverity.MODERATE,
        "country": "Russia",
        "region": "Eastern Europe",
        "supply_impact_bpd": 300000,
        "tags": ["Russia", "G7", "price cap", "sanctions"],
    },
    {
        "title": "Gulf of Mexico Platform Reports Production Halt Due to Weather",
        "event_type": EventType.NATURAL_DISASTER,
        "severity": EventSeverity.LOW,
        "country": "United States",
        "region": "North America",
        "supply_impact_bpd": 80000,
        "tags": ["Gulf of Mexico", "hurricane", "weather"],
    },
    {
        "title": "Sudan Civil Conflict Disrupts South Sudan Oil Export Routes",
        "event_type": EventType.CONFLICT,
        "severity": EventSeverity.HIGH,
        "country": "Sudan",
        "region": "East Africa",
        "supply_impact_bpd": 150000,
        "tags": ["Sudan", "South Sudan", "conflict", "pipeline"],
    },
]


class NewsCollector(BaseCollector):
    """
    Collects geopolitical news and converts to structured events.

    In production: integrates with NewsAPI or dedicated threat intelligence feeds.
    In development: generates simulated events for demonstration.
    """

    def __init__(
        self,
        recovery_manager: RecoveryManager,
        news_api_key: str = "",
        interval_seconds: int = 300,
    ):
        super().__init__("news_collector", recovery_manager, interval_seconds)
        self._api_key = news_api_key
        self._simulated = not bool(news_api_key)
        self._seen_titles: set = set()

    async def _fetch(self) -> List[dict]:
        if self._simulated:
            return self._simulate_events()
        return await self._fetch_news_api()

    def _simulate_events(self) -> List[dict]:
        """Generate simulated geopolitical events (1 in 3 chance per cycle)."""
        if random.random() > 0.33:
            return []
        template = random.choice(SIMULATED_NEWS_TEMPLATES)
        if template["title"] in self._seen_titles:
            return []
        self._seen_titles.add(template["title"])
        return [{
            **template,
            "description": f"[Simulated] {template['title']}. Intelligence analysts are monitoring the situation for supply chain impact.",
            "source": "simulated_feed",
            "confidence_score": round(random.uniform(0.65, 0.92), 2),
        }]

    async def _fetch_news_api(self) -> List[dict]:
        url = "https://newsapi.org/v2/everything"
        params = {
            "apiKey": self._api_key,
            "q": "oil OR pipeline OR OPEC OR LNG sanctions",
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 10,
            "from": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            return [
                {
                    "title": a["title"],
                    "description": a.get("description", ""),
                    "source": "newsapi",
                    "source_url": a.get("url"),
                    "event_type": EventType.SUPPLY_DISRUPTION,
                    "severity": EventSeverity.MODERATE,
                    "country": "Unknown",
                    "region": "Global",
                    "confidence_score": 0.6,
                    "tags": ["news", "auto-classified"],
                }
                for a in articles
                if any(kw.lower() in (a.get("title", "") + a.get("description", "")).lower()
                       for kw in ENERGY_KEYWORDS)
            ]

    async def _process(self, raw_items: List[Any]) -> int:
        store = get_store()
        count = 0
        for item in raw_items:
            existing = store.filter("events", title=item["title"])
            if existing:
                continue
            event = GeopoliticalEvent(
                title=item["title"],
                description=item.get("description", item["title"]),
                event_type=item.get("event_type", EventType.SUPPLY_DISRUPTION),
                severity=item.get("severity", EventSeverity.MODERATE),
                status=EventStatus.MONITORING,
                country=item.get("country", "Unknown"),
                region=item.get("region", "Global"),
                supply_impact_bpd=item.get("supply_impact_bpd"),
                price_impact_pct=item.get("price_impact_pct"),
                source=item.get("source", "news"),
                source_url=item.get("source_url"),
                tags=item.get("tags", []),
                confidence_score=item.get("confidence_score", 0.7),
            )
            store.insert("events", event.model_dump())
            count += 1
            logger.info("event_ingested", event_id=event.id, title=event.title)
        return count
