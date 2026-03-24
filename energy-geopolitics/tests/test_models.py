"""Tests for data models."""
import pytest
from src.models import (
    GeopoliticalEvent, EventType, EventSeverity, EventStatus,
    EnergyAsset, AssetType, AssetStatus,
    RiskAssessment, RiskLevel,
)
from src.models.risk import RiskFactor
from src.models.intelligence import IntelligenceReport, ReportType, AlertNotification, AlertSeverity


def test_geopolitical_event_defaults():
    event = GeopoliticalEvent(
        title="Test Event",
        description="Test description",
        event_type=EventType.CONFLICT,
        severity=EventSeverity.HIGH,
        country="Test Country",
        region="Test Region",
    )
    assert event.id is not None
    assert event.status == EventStatus.MONITORING
    assert event.confidence_score == 1.0
    assert event.affected_assets == []
    assert event.tags == []


def test_geopolitical_event_with_impact():
    event = GeopoliticalEvent(
        title="Supply Disruption",
        description="Pipeline explosion",
        event_type=EventType.PIPELINE_INCIDENT,
        severity=EventSeverity.CRITICAL,
        country="Iraq",
        region="Middle East",
        supply_impact_bpd=500_000,
        price_impact_pct=2.5,
    )
    assert event.supply_impact_bpd == 500_000
    assert event.price_impact_pct == 2.5


def test_energy_asset_defaults():
    asset = EnergyAsset(
        name="Test Oilfield",
        asset_type=AssetType.OILFIELD,
        country="Saudi Arabia",
        region="Middle East",
        operator="Aramco",
    )
    assert asset.id is not None
    assert asset.status == AssetStatus.OPERATIONAL
    assert asset.strategic_importance == 0.5


def test_risk_assessment_creation():
    ra = RiskAssessment(
        overall_score=0.75,
        risk_level=RiskLevel.HIGH,
        geopolitical_score=0.80,
        supply_disruption_score=0.70,
        infrastructure_score=0.60,
        sanctions_score=0.50,
        market_volatility_score=0.65,
    )
    assert ra.id is not None
    assert ra.overall_score == 0.75
    assert ra.risk_level == RiskLevel.HIGH


def test_risk_factor():
    factor = RiskFactor(
        name="Test Factor",
        score=0.8,
        weight=0.9,
        description="Test risk factor",
        contributing_event_ids=["evt-1"],
    )
    assert factor.score == 0.8
    assert "evt-1" in factor.contributing_event_ids


def test_alert_notification():
    alert = AlertNotification(
        title="Test Alert",
        message="Test alert message",
        severity=AlertSeverity.CRITICAL,
    )
    assert alert.id is not None
    assert not alert.acknowledged


def test_intelligence_report():
    report = IntelligenceReport(
        title="Test Report",
        report_type=ReportType.DAILY_BRIEF,
        summary="Brief summary",
        full_content="Full content here",
        key_findings=["Finding 1", "Finding 2"],
        recommendations=["Action 1"],
    )
    assert report.id is not None
    assert len(report.key_findings) == 2
    assert report.classification == "UNCLASSIFIED"
