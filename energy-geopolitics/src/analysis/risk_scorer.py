"""Risk scoring engine for energy geopolitics."""
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from src.models import GeopoliticalEvent, EnergyAsset, EventType, EventSeverity, EventStatus
from src.models.risk import RiskAssessment, RiskLevel, RiskFactor, RegionalRiskSummary
from src.data.db import get_store
from src.logger import get_logger

logger = get_logger(__name__)

# Severity -> base score mapping
SEVERITY_SCORES = {
    EventSeverity.CRITICAL: 0.95,
    EventSeverity.HIGH: 0.75,
    EventSeverity.MODERATE: 0.50,
    EventSeverity.LOW: 0.25,
}

# Event type -> dimensional risk weights
# [geopolitical, supply_disruption, infrastructure, sanctions, market_volatility]
EVENT_DIMENSION_WEIGHTS: Dict[EventType, List[float]] = {
    EventType.CONFLICT:              [0.90, 0.70, 0.60, 0.10, 0.80],
    EventType.SANCTIONS:             [0.80, 0.85, 0.10, 0.95, 0.70],
    EventType.POLICY_CHANGE:         [0.70, 0.60, 0.05, 0.40, 0.65],
    EventType.SUPPLY_DISRUPTION:     [0.30, 0.95, 0.50, 0.05, 0.75],
    EventType.PIPELINE_INCIDENT:     [0.20, 0.80, 0.95, 0.05, 0.60],
    EventType.NATURAL_DISASTER:      [0.10, 0.70, 0.85, 0.00, 0.50],
    EventType.POLITICAL_INSTABILITY: [0.85, 0.55, 0.30, 0.20, 0.70],
    EventType.TRADE_DISPUTE:         [0.65, 0.65, 0.10, 0.50, 0.65],
    EventType.CARTEL_DECISION:       [0.40, 0.85, 0.00, 0.10, 0.90],
    EventType.INFRASTRUCTURE_ATTACK: [0.50, 0.85, 0.95, 0.10, 0.75],
}

RISK_LEVEL_THRESHOLDS = [
    (0.85, RiskLevel.CRITICAL),
    (0.70, RiskLevel.HIGH),
    (0.45, RiskLevel.MODERATE),
    (0.20, RiskLevel.LOW),
    (0.00, RiskLevel.MINIMAL),
]


def score_to_level(score: float) -> RiskLevel:
    for threshold, level in RISK_LEVEL_THRESHOLDS:
        if score >= threshold:
            return level
    return RiskLevel.MINIMAL


class RiskScorer:
    """
    Computes multi-dimensional risk scores for assets and regions.

    Factors in:
    - Active geopolitical events and their severity
    - Asset strategic importance
    - Supply disruption magnitude
    - Recency of events (exponential decay)
    """

    DECAY_HALF_LIFE_DAYS = 14.0  # Events halve in impact every 14 days

    def _event_recency_weight(self, event: GeopoliticalEvent) -> float:
        if event.status == EventStatus.ACTIVE:
            return 1.0
        age_days = (datetime.utcnow() - event.detected_at).total_seconds() / 86400
        return 0.5 ** (age_days / self.DECAY_HALF_LIFE_DAYS)

    def _score_event_for_dimensions(
        self, event: GeopoliticalEvent
    ) -> tuple:
        """Returns (geopolitical, supply, infra, sanctions, market) dimension scores."""
        weights = EVENT_DIMENSION_WEIGHTS.get(
            event.event_type, [0.5, 0.5, 0.5, 0.5, 0.5]
        )
        severity = SEVERITY_SCORES.get(event.severity, 0.5)
        recency = self._event_recency_weight(event)
        return tuple(w * severity * recency for w in weights)

    def score_asset(self, asset: EnergyAsset, events: List[GeopoliticalEvent]) -> RiskAssessment:
        """Compute risk assessment for a specific energy asset."""
        # Filter relevant events (affect this asset or its country)
        relevant = [
            e for e in events
            if (asset.id in e.affected_assets or e.country == asset.country)
            and e.status != EventStatus.RESOLVED
        ]

        geo_scores, supply_scores, infra_scores, sanc_scores, market_scores = [], [], [], [], []
        factors: List[RiskFactor] = []
        event_ids = []

        for event in relevant:
            g, s, i, sc, m = self._score_event_for_dimensions(event)
            geo_scores.append(g)
            supply_scores.append(s)
            infra_scores.append(i)
            sanc_scores.append(sc)
            market_scores.append(m)
            event_ids.append(event.id)

            # Add a risk factor entry
            factors.append(RiskFactor(
                name=event.title[:60],
                score=SEVERITY_SCORES.get(event.severity, 0.5),
                weight=self._event_recency_weight(event),
                description=f"{event.event_type.value} | {event.country}",
                contributing_event_ids=[event.id],
            ))

        def agg(scores: list) -> float:
            if not scores:
                return 0.0
            # Use max + average blend for a realistic aggregate
            return min(1.0, 0.6 * max(scores) + 0.4 * (sum(scores) / len(scores)))

        geo = agg(geo_scores)
        supply = agg(supply_scores)
        infra = agg(infra_scores)
        sanc = agg(sanc_scores)
        market = agg(market_scores)

        # Strategic importance amplifies all scores
        si = asset.strategic_importance
        overall = min(1.0, (
            geo * 0.25 + supply * 0.30 + infra * 0.20 + sanc * 0.15 + market * 0.10
        ) * (0.8 + 0.4 * si))

        supply_at_risk = None
        if asset.current_output_bpd and relevant:
            max_supply_score = max((s for _, s, _, _, _ in
                                    [self._score_event_for_dimensions(e) for e in relevant]), default=0)
            supply_at_risk = asset.current_output_bpd * max_supply_score

        return RiskAssessment(
            asset_id=asset.id,
            country=asset.country,
            region=asset.region,
            overall_score=round(overall, 4),
            risk_level=score_to_level(overall),
            geopolitical_score=round(geo, 4),
            supply_disruption_score=round(supply, 4),
            infrastructure_score=round(infra, 4),
            sanctions_score=round(sanc, 4),
            market_volatility_score=round(market, 4),
            risk_factors=factors,
            estimated_supply_at_risk_bpd=round(supply_at_risk, 0) if supply_at_risk else None,
            contributing_event_ids=event_ids,
            trend=self._compute_trend(overall),
        )

    def score_region(self, region: str) -> RiskAssessment:
        """Compute aggregate risk for a geographic region."""
        store = get_store()
        events = [
            GeopoliticalEvent(**e)
            for e in store.filter("events", region=region)
            if e.get("status") != EventStatus.RESOLVED
        ]
        # Also grab partial matches (events mentioning this region)
        all_events = [GeopoliticalEvent(**e) for e in store.list_all("events")]
        region_events = [e for e in all_events if region.lower() in e.region.lower()
                         and e.status != EventStatus.RESOLVED]

        return self._score_event_set(region=region, events=region_events)

    def score_global(self) -> RiskAssessment:
        """Compute global energy geopolitical risk."""
        store = get_store()
        events = [
            GeopoliticalEvent(**e) for e in store.list_all("events")
            if e.get("status") != EventStatus.RESOLVED
        ]
        return self._score_event_set(events=events)

    def _score_event_set(
        self,
        events: List[GeopoliticalEvent],
        region: Optional[str] = None,
    ) -> RiskAssessment:
        geo_scores, supply_scores, infra_scores, sanc_scores, market_scores = [], [], [], [], []
        factors: List[RiskFactor] = []
        event_ids = []
        total_supply_at_risk = 0.0

        for event in events:
            g, s, i, sc, m = self._score_event_for_dimensions(event)
            geo_scores.append(g)
            supply_scores.append(s)
            infra_scores.append(i)
            sanc_scores.append(sc)
            market_scores.append(m)
            event_ids.append(event.id)
            if event.supply_impact_bpd and event.supply_impact_bpd > 0:
                total_supply_at_risk += event.supply_impact_bpd * s

            factors.append(RiskFactor(
                name=event.title[:60],
                score=SEVERITY_SCORES.get(event.severity, 0.5),
                weight=self._event_recency_weight(event),
                description=f"{event.event_type.value} | {event.country}",
                contributing_event_ids=[event.id],
            ))

        def agg(scores: list) -> float:
            if not scores:
                return 0.0
            return min(1.0, 0.6 * max(scores) + 0.4 * (sum(scores) / len(scores)))

        geo = agg(geo_scores)
        supply = agg(supply_scores)
        infra = agg(infra_scores)
        sanc = agg(sanc_scores)
        market = agg(market_scores)
        overall = min(1.0, geo * 0.25 + supply * 0.30 + infra * 0.20 + sanc * 0.15 + market * 0.10)

        # Price impact estimate
        price_impact = None
        if total_supply_at_risk > 0:
            low_est = total_supply_at_risk / 1_000_000 * 0.5
            high_est = total_supply_at_risk / 1_000_000 * 2.0
            price_impact = {"low": round(low_est, 2), "high": round(high_est, 2)}

        return RiskAssessment(
            country=None,
            region=region,
            overall_score=round(overall, 4),
            risk_level=score_to_level(overall),
            geopolitical_score=round(geo, 4),
            supply_disruption_score=round(supply, 4),
            infrastructure_score=round(infra, 4),
            sanctions_score=round(sanc, 4),
            market_volatility_score=round(market, 4),
            risk_factors=sorted(factors, key=lambda f: f.score * f.weight, reverse=True)[:10],
            estimated_supply_at_risk_bpd=round(total_supply_at_risk, 0),
            estimated_price_impact_range=price_impact,
            contributing_event_ids=event_ids,
            trend=self._compute_trend(overall),
        )

    def _compute_trend(self, score: float) -> str:
        if score > 0.75:
            return "deteriorating"
        if score > 0.50:
            return "stable"
        return "improving"

    def regional_summary(self) -> List[RegionalRiskSummary]:
        store = get_store()
        all_events = [GeopoliticalEvent(**e) for e in store.list_all("events")]
        all_assets = [EnergyAsset(**a) for a in store.list_all("assets")]

        # Group by region
        regions: Dict[str, List] = {}
        for e in all_events:
            regions.setdefault(e.region, []).append(e)

        summaries = []
        for region, events in regions.items():
            active = [e for e in events if e.status != EventStatus.RESOLVED]
            ra = self._score_event_set(region=region, events=active)

            region_assets = [a for a in all_assets if a.region == region]
            at_risk_assets = [a for a in region_assets if a.active_risk_ids or ra.overall_score > 0.5]
            countries = list({e.country for e in events})
            total_supply = sum(
                e.supply_impact_bpd for e in active
                if e.supply_impact_bpd and e.supply_impact_bpd > 0
            )

            summaries.append(RegionalRiskSummary(
                region=region,
                countries=countries,
                avg_risk_score=ra.overall_score,
                risk_level=ra.risk_level,
                active_events=len(active),
                assets_at_risk=len(at_risk_assets),
                total_supply_at_risk_bpd=total_supply,
                last_updated=datetime.utcnow(),
            ))

        return sorted(summaries, key=lambda s: s.avg_risk_score, reverse=True)
