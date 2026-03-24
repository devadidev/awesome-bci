"""Alert generation engine for critical risk thresholds."""
from datetime import datetime
from typing import List, Optional
from src.models import GeopoliticalEvent, EnergyAsset, EventSeverity, EventStatus
from src.models.intelligence import AlertNotification, AlertSeverity
from src.models.risk import RiskAssessment, RiskLevel
from src.data.db import get_store
from src.logger import get_logger

logger = get_logger(__name__)


class AlertEngine:
    """
    Generates alert notifications when risk thresholds are breached.

    Rules:
    - New CRITICAL severity event -> CRITICAL alert
    - Risk score > 0.85 for any asset -> CRITICAL alert
    - Risk score > 0.70 -> HIGH alert
    - Supply disruption > 1M bpd -> HIGH alert
    - New SANCTIONS event -> WARNING
    """

    HIGH_RISK_THRESHOLD = 0.70
    CRITICAL_RISK_THRESHOLD = 0.85
    LARGE_SUPPLY_DISRUPTION_BPD = 1_000_000

    def evaluate_event(self, event: GeopoliticalEvent) -> Optional[AlertNotification]:
        """Check if a new event warrants an alert."""
        if event.severity == EventSeverity.CRITICAL:
            return AlertNotification(
                title=f"CRITICAL EVENT: {event.title[:80]}",
                message=(
                    f"A CRITICAL severity event has been detected in {event.region}. "
                    f"Supply impact: {event.supply_impact_bpd:,.0f} bpd. "
                    f"Immediate assessment required."
                ) if event.supply_impact_bpd else (
                    f"A CRITICAL severity event has been detected in {event.region}."
                ),
                severity=AlertSeverity.CRITICAL,
                event_id=event.id,
                metadata={"country": event.country, "type": event.event_type.value},
            )
        elif event.severity == EventSeverity.HIGH:
            if event.supply_impact_bpd and event.supply_impact_bpd >= self.LARGE_SUPPLY_DISRUPTION_BPD:
                return AlertNotification(
                    title=f"LARGE SUPPLY DISRUPTION: {event.title[:70]}",
                    message=(
                        f"Supply disruption of {event.supply_impact_bpd:,.0f} bpd detected. "
                        f"Region: {event.region}. Monitor for price impact."
                    ),
                    severity=AlertSeverity.HIGH,
                    event_id=event.id,
                    metadata={"supply_impact_bpd": str(event.supply_impact_bpd)},
                )
        return None

    def evaluate_risk(self, assessment: RiskAssessment) -> Optional[AlertNotification]:
        """Check if a risk assessment warrants an alert."""
        if assessment.overall_score >= self.CRITICAL_RISK_THRESHOLD:
            target = assessment.asset_id or assessment.region or "Global"
            return AlertNotification(
                title=f"CRITICAL RISK: {target}",
                message=(
                    f"Risk score {assessment.overall_score:.2f} ({assessment.risk_level.value.upper()}) "
                    f"for {target}. Supply at risk: "
                    f"{assessment.estimated_supply_at_risk_bpd:,.0f} bpd"
                    if assessment.estimated_supply_at_risk_bpd else
                    f"Risk score {assessment.overall_score:.2f} ({assessment.risk_level.value.upper()}) for {target}."
                ),
                severity=AlertSeverity.CRITICAL,
                asset_id=assessment.asset_id,
                risk_score=assessment.overall_score,
                metadata={"risk_level": assessment.risk_level.value},
            )
        elif assessment.overall_score >= self.HIGH_RISK_THRESHOLD:
            target = assessment.asset_id or assessment.region or "Global"
            return AlertNotification(
                title=f"HIGH RISK: {target}",
                message=f"Risk score elevated to {assessment.overall_score:.2f} for {target}.",
                severity=AlertSeverity.HIGH,
                asset_id=assessment.asset_id,
                risk_score=assessment.overall_score,
                metadata={"risk_level": assessment.risk_level.value},
            )
        return None

    def run_full_scan(self) -> List[AlertNotification]:
        """Scan all events and assets, generate pending alerts."""
        store = get_store()
        alerts = []
        existing_alert_events = {
            a.get("event_id") for a in store.list_all("alerts") if a.get("event_id")
        }

        # Check unalerted critical/high events
        for event_data in store.list_all("events"):
            event = GeopoliticalEvent(**event_data)
            if event.id in existing_alert_events:
                continue
            if event.status == EventStatus.RESOLVED:
                continue
            alert = self.evaluate_event(event)
            if alert:
                store.insert("alerts", alert.model_dump())
                alerts.append(alert)
                logger.info("alert_generated", alert_id=alert.id, severity=alert.severity)

        logger.info("alert_scan_complete", new_alerts=len(alerts))
        return alerts

    def acknowledge_alert(self, alert_id: str) -> bool:
        store = get_store()
        updated = store.update(
            "alerts",
            alert_id,
            {"acknowledged": True, "acknowledged_at": datetime.utcnow().isoformat()},
        )
        return updated is not None
