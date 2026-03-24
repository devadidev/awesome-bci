"""Supply chain and market impact analysis."""
from typing import List, Dict, Optional
from src.models import GeopoliticalEvent, EnergyAsset, EventStatus
from src.data.db import get_store
from src.logger import get_logger

logger = get_logger(__name__)

GLOBAL_DEMAND_BPD = 102_000_000   # ~102 million bpd global oil demand (2024)
PRICE_ELASTICITY = -0.05           # % price change per 1% supply change (short-run)


class ImpactAnalyzer:
    """Analyzes supply chain and price impact of geopolitical events."""

    def global_supply_at_risk(self) -> dict:
        store = get_store()
        events = [
            GeopoliticalEvent(**e) for e in store.list_all("events")
            if e.get("status") != EventStatus.RESOLVED
        ]
        total_at_risk = sum(
            e.supply_impact_bpd for e in events
            if e.supply_impact_bpd and e.supply_impact_bpd > 0
        )
        pct_of_global = (total_at_risk / GLOBAL_DEMAND_BPD) * 100
        price_impact_est = abs(pct_of_global * PRICE_ELASTICITY)

        return {
            "total_supply_at_risk_bpd": round(total_at_risk, 0),
            "global_demand_bpd": GLOBAL_DEMAND_BPD,
            "pct_of_global_supply": round(pct_of_global, 2),
            "estimated_price_impact_pct": round(price_impact_est, 2),
            "active_events": len(events),
            "breakdown_by_region": self._breakdown_by_region(events),
            "breakdown_by_type": self._breakdown_by_type(events),
        }

    def _breakdown_by_region(self, events: List[GeopoliticalEvent]) -> Dict[str, float]:
        result: Dict[str, float] = {}
        for e in events:
            if e.supply_impact_bpd and e.supply_impact_bpd > 0:
                result[e.region] = result.get(e.region, 0) + e.supply_impact_bpd
        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))

    def _breakdown_by_type(self, events: List[GeopoliticalEvent]) -> Dict[str, float]:
        result: Dict[str, float] = {}
        for e in events:
            if e.supply_impact_bpd and e.supply_impact_bpd > 0:
                key = e.event_type.value
                result[key] = result.get(key, 0) + e.supply_impact_bpd
        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))

    def asset_exposure(self, asset_id: str) -> Optional[dict]:
        store = get_store()
        asset_data = store.get("assets", asset_id)
        if not asset_data:
            return None
        asset = EnergyAsset(**asset_data)

        events = [
            GeopoliticalEvent(**e) for e in store.list_all("events")
            if (asset_id in e.get("affected_assets", []) or e.get("country") == asset.country)
            and e.get("status") != EventStatus.RESOLVED
        ]

        total_at_risk = 0.0
        if asset.current_output_bpd:
            # Worst-case: most severe event that could cut output
            max_impact_pct = max(
                (SEVERITY_SCORES_SIMPLE.get(e.severity, 0.5) for e in events), default=0
            )
            total_at_risk = asset.current_output_bpd * max_impact_pct

        return {
            "asset_id": asset_id,
            "asset_name": asset.name,
            "country": asset.country,
            "region": asset.region,
            "current_output_bpd": asset.current_output_bpd,
            "output_at_risk_bpd": round(total_at_risk, 0),
            "active_threat_count": len(events),
            "threats": [
                {
                    "event_id": e.id,
                    "title": e.title,
                    "type": e.event_type.value,
                    "severity": e.severity.value,
                }
                for e in events
            ],
        }

    def chokepoint_risk(self) -> List[dict]:
        store = get_store()
        from src.models import AssetType
        chokepoints = [
            EnergyAsset(**a) for a in store.list_all("assets")
            if a.get("asset_type") == AssetType.CHOKEPOINT
        ]
        result = []
        for cp in chokepoints:
            exposure = self.asset_exposure(cp.id)
            if exposure:
                result.append({
                    **exposure,
                    "strategic_importance": cp.strategic_importance,
                    "pct_global_flow": round(
                        (cp.current_output_bpd or 0) / GLOBAL_DEMAND_BPD * 100, 1
                    ),
                })
        return sorted(result, key=lambda x: x["strategic_importance"], reverse=True)


# Simplified severity scores for impact analysis
SEVERITY_SCORES_SIMPLE = {
    "critical": 0.80,
    "high": 0.55,
    "moderate": 0.30,
    "low": 0.10,
}
