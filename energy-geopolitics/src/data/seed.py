"""Seed realistic oil & gas geopolitical data for MVP demonstration."""
from datetime import datetime, timedelta
from src.models import (
    GeopoliticalEvent, EventType, EventSeverity, EventStatus,
    EnergyAsset, AssetType, AssetStatus,
)
from src.models.intelligence import OilPriceSnapshot
from src.data.db import get_store
from src.logger import get_logger

logger = get_logger(__name__)


SEED_ASSETS = [
    {
        "name": "Ghawar Oil Field",
        "asset_type": AssetType.OILFIELD,
        "country": "Saudi Arabia",
        "region": "Middle East",
        "operator": "Saudi Aramco",
        "capacity_bpd": 3800000,
        "current_output_bpd": 3600000,
        "strategic_importance": 0.98,
    },
    {
        "name": "Strait of Hormuz",
        "asset_type": AssetType.CHOKEPOINT,
        "country": "International",
        "region": "Middle East",
        "operator": "International Waters",
        "capacity_bpd": 21000000,
        "current_output_bpd": 20500000,
        "strategic_importance": 1.0,
    },
    {
        "name": "Permian Basin",
        "asset_type": AssetType.OILFIELD,
        "country": "United States",
        "region": "North America",
        "operator": "Multiple Operators",
        "capacity_bpd": 6000000,
        "current_output_bpd": 5800000,
        "strategic_importance": 0.90,
    },
    {
        "name": "Trans-Siberian Pipeline",
        "asset_type": AssetType.PIPELINE,
        "country": "Russia",
        "region": "Eastern Europe / Asia",
        "operator": "Transneft",
        "capacity_bpd": 2000000,
        "current_output_bpd": 1200000,
        "strategic_importance": 0.82,
    },
    {
        "name": "Ras Tanura Export Terminal",
        "asset_type": AssetType.EXPORT_TERMINAL,
        "country": "Saudi Arabia",
        "region": "Middle East",
        "operator": "Saudi Aramco",
        "capacity_bpd": 6500000,
        "current_output_bpd": 6200000,
        "strategic_importance": 0.95,
    },
    {
        "name": "Bab el-Mandeb Strait",
        "asset_type": AssetType.CHOKEPOINT,
        "country": "International",
        "region": "East Africa / Red Sea",
        "operator": "International Waters",
        "capacity_bpd": 6200000,
        "current_output_bpd": 4800000,
        "strategic_importance": 0.88,
        "status": AssetStatus.DEGRADED,
    },
    {
        "name": "Kashagan Oil Field",
        "asset_type": AssetType.OFFSHORE_PLATFORM,
        "country": "Kazakhstan",
        "region": "Central Asia",
        "operator": "NCOC Consortium",
        "capacity_bpd": 370000,
        "current_output_bpd": 310000,
        "strategic_importance": 0.72,
    },
    {
        "name": "Rotterdam Refinery Complex",
        "asset_type": AssetType.REFINERY,
        "country": "Netherlands",
        "region": "Western Europe",
        "operator": "Shell / BP / ExxonMobil",
        "capacity_bpd": 1200000,
        "current_output_bpd": 1100000,
        "strategic_importance": 0.85,
    },
]

SEED_EVENTS = [
    {
        "title": "Houthi Attacks on Red Sea Shipping Routes",
        "description": "Houthi forces continue missile and drone attacks on commercial vessels in the Red Sea, forcing major shipping companies to reroute around the Cape of Good Hope. LNG tankers and crude oil carriers have been affected, adding 10-14 days transit time and increasing freight costs.",
        "event_type": EventType.INFRASTRUCTURE_ATTACK,
        "severity": EventSeverity.HIGH,
        "status": EventStatus.ACTIVE,
        "country": "Yemen",
        "region": "Red Sea / Middle East",
        "supply_impact_bpd": 1400000,
        "price_impact_pct": 3.5,
        "source": "intelligence_feed",
        "tags": ["shipping", "LNG", "tankers", "Houthi", "Red Sea"],
        "confidence_score": 0.95,
    },
    {
        "title": "Russia-Ukraine Conflict: Continued Energy Infrastructure Targeting",
        "description": "Ongoing conflict continues to disrupt Russian energy exports via pipeline networks. EU sanctions package restricts seaborne crude imports. Several Ukrainian energy storage facilities have been targeted, impacting regional gas distribution.",
        "event_type": EventType.CONFLICT,
        "severity": EventSeverity.CRITICAL,
        "status": EventStatus.ACTIVE,
        "country": "Russia / Ukraine",
        "region": "Eastern Europe",
        "supply_impact_bpd": 2100000,
        "price_impact_pct": 6.2,
        "source": "intelligence_feed",
        "tags": ["Russia", "Ukraine", "pipeline", "sanctions", "war"],
        "confidence_score": 0.98,
    },
    {
        "title": "OPEC+ Production Cut Extension",
        "description": "OPEC+ coalition announced extension of voluntary production cuts of 2.2 million barrels per day through Q2. Saudi Arabia leads with 1 million bpd individual cut. Decision driven by demand concerns and price stabilization strategy.",
        "event_type": EventType.CARTEL_DECISION,
        "severity": EventSeverity.HIGH,
        "status": EventStatus.ACTIVE,
        "country": "Saudi Arabia",
        "region": "Global",
        "supply_impact_bpd": 2200000,
        "price_impact_pct": 4.8,
        "source": "opec_official",
        "tags": ["OPEC+", "production cut", "Saudi Arabia", "supply"],
        "confidence_score": 1.0,
    },
    {
        "title": "Iran Nuclear Talks Breakdown - Sanctions Remain",
        "description": "US-Iran nuclear negotiations collapsed without agreement. Existing sanctions on Iranian oil exports remain in force, limiting Iran to shadow fleet exports. Estimated 1.2 million bpd locked out of formal markets.",
        "event_type": EventType.SANCTIONS,
        "severity": EventSeverity.MODERATE,
        "status": EventStatus.MONITORING,
        "country": "Iran",
        "region": "Middle East",
        "supply_impact_bpd": 1200000,
        "price_impact_pct": 2.1,
        "source": "state_dept_feed",
        "tags": ["Iran", "sanctions", "nuclear", "JCPOA"],
        "confidence_score": 0.88,
    },
    {
        "title": "Libya Production Disruption - Eastern Blockade",
        "description": "Armed factions have blocked Libyan oil exports from eastern fields. National Oil Corporation declared force majeure on contracts from Sharara and Waha fields, reducing output by approximately 400,000 bpd.",
        "event_type": EventType.SUPPLY_DISRUPTION,
        "severity": EventSeverity.HIGH,
        "status": EventStatus.ACTIVE,
        "country": "Libya",
        "region": "North Africa",
        "supply_impact_bpd": 400000,
        "price_impact_pct": 1.8,
        "source": "noc_official",
        "tags": ["Libya", "force majeure", "armed groups", "NOC"],
        "confidence_score": 0.92,
    },
    {
        "title": "Venezuela PDVSA Partial Sanction Easing",
        "description": "US Treasury issued limited 6-month license allowing Chevron to resume Venezuelan crude lifting. Production capacity estimated at 900,000 bpd with potential to reach 1.1 million bpd under full operations. License contingent on electoral concessions.",
        "event_type": EventType.SANCTIONS,
        "severity": EventSeverity.MODERATE,
        "status": EventStatus.MONITORING,
        "country": "Venezuela",
        "region": "Latin America",
        "supply_impact_bpd": -200000,  # Negative = supply increase
        "price_impact_pct": -0.8,
        "source": "us_treasury",
        "tags": ["Venezuela", "PDVSA", "Chevron", "sanctions relief"],
        "confidence_score": 0.85,
    },
    {
        "title": "Iraq Kirkuk-Ceyhan Pipeline Restart Delayed",
        "description": "Restart of the Iraq-Turkey Kirkuk-Ceyhan pipeline (450,000 bpd capacity) delayed again following technical disputes and Kurdish Regional Government revenue sharing disagreements. Pipeline has been offline for over 13 months.",
        "event_type": EventType.PIPELINE_INCIDENT,
        "severity": EventSeverity.MODERATE,
        "status": EventStatus.MONITORING,
        "country": "Iraq",
        "region": "Middle East",
        "supply_impact_bpd": 450000,
        "price_impact_pct": 1.5,
        "source": "ministry_of_oil_iraq",
        "tags": ["Iraq", "Kurdistan", "pipeline", "Turkey", "Ceyhan"],
        "confidence_score": 0.90,
    },
]

SEED_PRICES = [
    {"brent": 82.40, "wti": 78.20, "nat_gas": 2.85, "days_ago": 7},
    {"brent": 83.10, "wti": 78.90, "nat_gas": 2.92, "days_ago": 6},
    {"brent": 84.50, "wti": 80.10, "nat_gas": 3.01, "days_ago": 5},
    {"brent": 83.80, "wti": 79.60, "nat_gas": 2.98, "days_ago": 4},
    {"brent": 85.20, "wti": 81.00, "nat_gas": 3.10, "days_ago": 3},
    {"brent": 86.10, "wti": 81.80, "nat_gas": 3.15, "days_ago": 2},
    {"brent": 85.60, "wti": 81.30, "nat_gas": 3.08, "days_ago": 1},
    {"brent": 87.20, "wti": 82.90, "nat_gas": 3.22, "days_ago": 0},
]


def load_seed_data() -> None:
    store = get_store()

    # Skip if already seeded
    if store.list_all("assets"):
        logger.info("seed_data_already_loaded")
        return

    logger.info("loading_seed_data")

    # Seed assets
    asset_ids = {}
    for data in SEED_ASSETS:
        status = data.pop("status", AssetStatus.OPERATIONAL)
        asset = EnergyAsset(status=status, **data)
        store.insert("assets", asset.model_dump())
        asset_ids[asset.name] = asset.id

    # Seed events - link assets
    event_asset_map = {
        "Houthi Attacks on Red Sea Shipping Routes": ["Bab el-Mandeb Strait"],
        "Russia-Ukraine Conflict: Continued Energy Infrastructure Targeting": ["Trans-Siberian Pipeline"],
        "Iraq Kirkuk-Ceyhan Pipeline Restart Delayed": [],
    }
    for data in SEED_EVENTS:
        linked = event_asset_map.get(data["title"], [])
        data["affected_assets"] = [asset_ids[n] for n in linked if n in asset_ids]
        event = GeopoliticalEvent(**data)
        store.insert("events", event.model_dump())

    # Seed price history
    now = datetime.utcnow()
    for p in SEED_PRICES:
        ts = now - timedelta(days=p["days_ago"])
        prev_idx = max(0, SEED_PRICES.index(p) - 1)
        prev_brent = SEED_PRICES[prev_idx]["brent"]
        change_pct = ((p["brent"] - prev_brent) / prev_brent) * 100
        snapshot = OilPriceSnapshot(
            timestamp=ts,
            brent_crude_usd=p["brent"],
            wti_crude_usd=p["wti"],
            natural_gas_usd=p["nat_gas"],
            change_24h_pct=round(change_pct, 2),
            source="seed_data",
        )
        store.append_price(snapshot.model_dump())

    counts = store.stats()
    logger.info("seed_data_loaded", **counts)
