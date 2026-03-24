"""Intelligence reports, risk assessments, and alerts routes."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from src.models.intelligence import IntelligenceReport, AlertNotification
from src.models.risk import RiskAssessment, RegionalRiskSummary
from src.data.db import get_store
from src.analysis.risk_scorer import RiskScorer
from src.analysis.impact_analyzer import ImpactAnalyzer
from src.analysis.alert_engine import AlertEngine
from src.services.intelligence_service import IntelligenceService
from src.logger import get_logger

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])
logger = get_logger(__name__)

scorer = RiskScorer()
analyzer = ImpactAnalyzer()
alert_engine = AlertEngine()
intel_service = IntelligenceService()


# ── Risk ──────────────────────────────────────────────────────────────────────

@router.get("/risk/global", response_model=RiskAssessment)
async def global_risk():
    """Compute current global energy geopolitical risk."""
    return scorer.score_global()


@router.get("/risk/regional", response_model=List[RegionalRiskSummary])
async def regional_risk():
    """Get risk summary for all monitored regions, sorted by risk score."""
    return scorer.regional_summary()


@router.get("/risk/asset/{asset_id}", response_model=RiskAssessment)
async def asset_risk(asset_id: str):
    """Compute risk assessment for a specific energy asset."""
    store = get_store()
    asset_data = store.get("assets", asset_id)
    if not asset_data:
        raise HTTPException(status_code=404, detail="Asset not found")

    from src.models import EnergyAsset, GeopoliticalEvent, EventStatus
    asset = EnergyAsset(**asset_data)
    events = [
        GeopoliticalEvent(**e) for e in store.list_all("events")
        if e.get("status") != EventStatus.RESOLVED
    ]
    return scorer.score_asset(asset, events)


# ── Supply chain impact ───────────────────────────────────────────────────────

@router.get("/impact/global")
async def global_supply_impact():
    """Get global supply chain impact analysis."""
    return analyzer.global_supply_at_risk()


@router.get("/impact/chokepoints")
async def chokepoint_analysis():
    """Analyze risk exposure for all strategic chokepoints."""
    return analyzer.chokepoint_risk()


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports", response_model=List[IntelligenceReport])
async def list_reports(limit: int = Query(20, ge=1, le=100)):
    return intel_service.get_reports(limit=limit)


@router.post("/reports/daily-brief", response_model=IntelligenceReport, status_code=201)
async def generate_daily_brief():
    """Generate a fresh daily intelligence brief."""
    return intel_service.generate_daily_brief()


@router.get("/reports/{report_id}", response_model=IntelligenceReport)
async def get_report(report_id: str):
    store = get_store()
    report = store.get("intelligence", report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return IntelligenceReport(**report)


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=List[AlertNotification])
async def list_alerts(
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    store = get_store()
    alerts = store.list_all("alerts")
    if acknowledged is not None:
        alerts = [a for a in alerts if a.get("acknowledged") == acknowledged]
    alerts = sorted(alerts, key=lambda a: a.get("triggered_at", ""), reverse=True)
    return [AlertNotification(**a) for a in alerts[:limit]]


@router.post("/alerts/scan")
async def run_alert_scan():
    """Run full alert scan across all active events."""
    new_alerts = alert_engine.run_full_scan()
    return {"new_alerts": len(new_alerts), "alert_ids": [a.id for a in new_alerts]}


@router.patch("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    success = alert_engine.acknowledge_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"acknowledged": True}


# ── Prices ────────────────────────────────────────────────────────────────────

@router.get("/prices/latest")
async def latest_price():
    store = get_store()
    price = store.latest_price()
    if not price:
        raise HTTPException(status_code=404, detail="No price data available")
    return price


@router.get("/prices/history")
async def price_history(limit: int = Query(100, ge=1, le=1000)):
    store = get_store()
    return store.price_history(limit=limit)
