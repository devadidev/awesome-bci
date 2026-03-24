"""Tests for risk scoring engine."""
import pytest
from src.models import GeopoliticalEvent, EnergyAsset, AssetType, EventType, EventSeverity, EventStatus
from src.analysis.risk_scorer import RiskScorer, score_to_level
from src.models.risk import RiskLevel


def make_event(severity=EventSeverity.HIGH, event_type=EventType.CONFLICT,
               status=EventStatus.ACTIVE, country="TestCountry"):
    return GeopoliticalEvent(
        title=f"Test {severity} {event_type}",
        description="Test event",
        event_type=event_type,
        severity=severity,
        status=status,
        country=country,
        region="Test Region",
    )


def make_asset(country="TestCountry", strategic_importance=0.8, output=1_000_000):
    return EnergyAsset(
        name="Test Asset",
        asset_type=AssetType.OILFIELD,
        country=country,
        region="Test Region",
        operator="Test Corp",
        current_output_bpd=output,
        strategic_importance=strategic_importance,
    )


def test_score_to_level():
    assert score_to_level(0.90) == RiskLevel.CRITICAL
    assert score_to_level(0.75) == RiskLevel.HIGH
    assert score_to_level(0.50) == RiskLevel.MODERATE
    assert score_to_level(0.30) == RiskLevel.LOW
    assert score_to_level(0.10) == RiskLevel.MINIMAL


def test_asset_risk_no_events():
    scorer = RiskScorer()
    asset = make_asset()
    assessment = scorer.score_asset(asset, [])
    assert assessment.overall_score == 0.0
    assert assessment.risk_level == RiskLevel.MINIMAL
    assert assessment.contributing_event_ids == []


def test_asset_risk_with_critical_event():
    scorer = RiskScorer()
    asset = make_asset()
    event = make_event(severity=EventSeverity.CRITICAL, event_type=EventType.CONFLICT)
    assessment = scorer.score_asset(asset, [event])
    assert assessment.overall_score > 0.0
    assert assessment.risk_level in (RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.CRITICAL)
    assert event.id in assessment.contributing_event_ids


def test_asset_risk_different_country_not_included():
    scorer = RiskScorer()
    asset = make_asset(country="CountryA")
    event = make_event(severity=EventSeverity.CRITICAL, country="CountryB")
    event.affected_assets = []
    assessment = scorer.score_asset(asset, [event])
    # Event is from different country and not in affected_assets
    assert assessment.overall_score == 0.0


def test_asset_risk_in_affected_assets():
    scorer = RiskScorer()
    asset = make_asset(country="CountryA")
    event = make_event(severity=EventSeverity.HIGH, country="CountryB")
    event.affected_assets = [asset.id]
    assessment = scorer.score_asset(asset, [event])
    assert assessment.overall_score > 0.0


def test_sanctions_event_high_sanctions_score():
    scorer = RiskScorer()
    asset = make_asset()
    event = make_event(severity=EventSeverity.HIGH, event_type=EventType.SANCTIONS)
    assessment = scorer.score_asset(asset, [event])
    assert assessment.sanctions_score > assessment.infrastructure_score


def test_resolved_events_excluded():
    scorer = RiskScorer()
    asset = make_asset()
    event = make_event(severity=EventSeverity.CRITICAL)
    event.status = EventStatus.RESOLVED
    assessment = scorer.score_asset(asset, [event])
    assert assessment.overall_score == 0.0


def test_multiple_events_increase_score():
    scorer = RiskScorer()
    asset = make_asset()
    events = [
        make_event(severity=EventSeverity.MODERATE, event_type=EventType.SANCTIONS),
        make_event(severity=EventSeverity.HIGH, event_type=EventType.CONFLICT),
        make_event(severity=EventSeverity.HIGH, event_type=EventType.SUPPLY_DISRUPTION),
    ]
    single = scorer.score_asset(asset, [events[0]])
    multiple = scorer.score_asset(asset, events)
    assert multiple.overall_score >= single.overall_score


def test_supply_at_risk_calculated():
    scorer = RiskScorer()
    asset = make_asset(output=1_000_000)
    event = make_event(severity=EventSeverity.HIGH, event_type=EventType.SUPPLY_DISRUPTION)
    assessment = scorer.score_asset(asset, [event])
    assert assessment.estimated_supply_at_risk_bpd is not None
    assert assessment.estimated_supply_at_risk_bpd > 0
