"""Intelligence report generation service."""
from datetime import datetime, timedelta
from typing import List, Optional
from src.models import GeopoliticalEvent, EnergyAsset, EventSeverity, EventStatus
from src.models.intelligence import IntelligenceReport, ReportType, OilPriceSnapshot
from src.models.risk import RiskAssessment
from src.data.db import get_store
from src.analysis.risk_scorer import RiskScorer
from src.analysis.impact_analyzer import ImpactAnalyzer
from src.logger import get_logger

logger = get_logger(__name__)


class IntelligenceService:
    """Generates structured intelligence reports from event data and risk assessments."""

    def __init__(self):
        self._scorer = RiskScorer()
        self._analyzer = ImpactAnalyzer()

    def generate_daily_brief(self) -> IntelligenceReport:
        """Generate a daily intelligence brief covering all active events."""
        store = get_store()
        events = [GeopoliticalEvent(**e) for e in store.list_all("events")]
        active = [e for e in events if e.status != EventStatus.RESOLVED]
        critical = [e for e in active if e.severity == EventSeverity.CRITICAL]
        high = [e for e in active if e.severity == EventSeverity.HIGH]

        global_risk = self._scorer.score_global()
        impact = self._analyzer.global_supply_at_risk()
        price = store.latest_price()

        price_snapshot = OilPriceSnapshot(**price) if price else None

        key_findings = [
            f"Global energy risk score: {global_risk.overall_score:.2f} ({global_risk.risk_level.value.upper()})",
            f"{len(active)} active geopolitical events monitored ({len(critical)} critical, {len(high)} high)",
            f"Total supply at risk: {impact['total_supply_at_risk_bpd']:,.0f} bpd "
            f"({impact['pct_of_global_supply']:.1f}% of global demand)",
        ]

        if price_snapshot and price_snapshot.brent_crude_usd:
            trend = ""
            if price_snapshot.change_24h_pct:
                trend = f"({'↑' if price_snapshot.change_24h_pct > 0 else '↓'}{abs(price_snapshot.change_24h_pct):.2f}%)"
            key_findings.append(
                f"Brent crude: ${price_snapshot.brent_crude_usd:.2f}/bbl {trend}"
            )

        if critical:
            key_findings.append(
                f"Critical events requiring immediate attention: {', '.join(e.country for e in critical[:3])}"
            )

        # Top regions by risk
        regional = self._scorer.regional_summary()
        top_regions = regional[:3]
        for r in top_regions:
            key_findings.append(
                f"{r.region}: {r.risk_level.value.upper()} risk, "
                f"{r.active_events} active events, "
                f"{r.total_supply_at_risk_bpd:,.0f} bpd at risk"
            )

        recommendations = self._generate_recommendations(global_risk, active, impact)

        full_content = self._build_full_brief(
            active, global_risk, impact, regional, price_snapshot
        )

        report = IntelligenceReport(
            title=f"Energy Geopolitics Daily Brief — {datetime.utcnow().strftime('%Y-%m-%d')}",
            report_type=ReportType.DAILY_BRIEF,
            summary=(
                f"Global energy risk is {global_risk.risk_level.value.upper()} at {global_risk.overall_score:.2f}. "
                f"{len(active)} active events affect {impact['total_supply_at_risk_bpd']:,.0f} bpd "
                f"({impact['pct_of_global_supply']:.1f}% of global supply)."
            ),
            full_content=full_content,
            key_findings=key_findings,
            recommendations=recommendations,
            referenced_event_ids=[e.id for e in active[:20]],
            price_snapshot=price_snapshot,
            regions_covered=list({e.region for e in active}),
            confidence_level=0.85,
            valid_until=datetime.utcnow() + timedelta(hours=24),
        )
        store.insert("intelligence", report.model_dump())
        logger.info("daily_brief_generated", report_id=report.id)
        return report

    def _generate_recommendations(
        self, risk: RiskAssessment, events: list, impact: dict
    ) -> List[str]:
        recs = []
        if risk.overall_score > 0.85:
            recs.append("Activate emergency supply contingency plans and notify key stakeholders.")
        if risk.overall_score > 0.70:
            recs.append("Review physical delivery contracts for force majeure clauses.")
            recs.append("Increase strategic petroleum reserve drawdown readiness.")
        if impact["pct_of_global_supply"] > 3.0:
            recs.append("Coordinate with IEA member states on coordinated stock release options.")
        sanctions_events = [e for e in events if e.event_type.value == "sanctions"]
        if sanctions_events:
            recs.append("Verify all counterparty compliance with current sanctions regimes.")
        if not recs:
            recs.append("Continue monitoring; no immediate action required.")
            recs.append("Maintain hedge positions consistent with current risk level.")
        return recs

    def _build_full_brief(
        self,
        events: list,
        risk: RiskAssessment,
        impact: dict,
        regional: list,
        price: Optional[OilPriceSnapshot],
    ) -> str:
        lines = [
            f"# Energy Geopolitics Intelligence Brief",
            f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Classification**: UNCLASSIFIED",
            "",
            "## Executive Summary",
            f"Global energy geopolitical risk is assessed at **{risk.overall_score:.2f}** "
            f"({risk.risk_level.value.upper()}). A total of **{len(events)}** active events "
            f"are being monitored, with an estimated **{impact['total_supply_at_risk_bpd']:,.0f} bpd** "
            f"({impact['pct_of_global_supply']:.1f}% of global demand) at risk.",
            "",
        ]

        if price:
            lines += [
                "## Market Prices",
                f"- Brent Crude: **${price.brent_crude_usd:.2f}/bbl**"
                + (f" ({'+' if (price.change_24h_pct or 0) >= 0 else ''}{price.change_24h_pct:.2f}%)" if price.change_24h_pct else ""),
                f"- WTI Crude: **${price.wti_crude_usd:.2f}/bbl**" if price.wti_crude_usd else "",
                f"- Natural Gas: **${price.natural_gas_usd:.2f}/MMBtu**" if price.natural_gas_usd else "",
                "",
            ]

        lines += ["## Risk Dimensions", ""]
        dims = [
            ("Geopolitical", risk.geopolitical_score),
            ("Supply Disruption", risk.supply_disruption_score),
            ("Infrastructure", risk.infrastructure_score),
            ("Sanctions", risk.sanctions_score),
            ("Market Volatility", risk.market_volatility_score),
        ]
        for name, score in dims:
            bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
            lines.append(f"- {name:20s} [{bar}] {score:.2f}")
        lines.append("")

        lines += ["## Active Events by Region", ""]
        breakdown = impact.get("breakdown_by_region", {})
        for region, bpd in list(breakdown.items())[:8]:
            lines.append(f"- **{region}**: {bpd:,.0f} bpd at risk")
        lines.append("")

        lines += ["## Key Events", ""]
        critical = [e for e in events if e.severity == EventSeverity.CRITICAL]
        high = [e for e in events if e.severity == EventSeverity.HIGH]
        for e in (critical + high)[:8]:
            lines.append(f"### {e.title}")
            lines.append(f"*Severity*: {e.severity.value.upper()} | *Type*: {e.event_type.value} | *Country*: {e.country}")
            lines.append(f"{e.description[:300]}...")
            if e.supply_impact_bpd:
                lines.append(f"*Supply Impact*: {e.supply_impact_bpd:,.0f} bpd")
            lines.append("")

        return "\n".join(lines)

    def get_reports(self, limit: int = 20) -> List[IntelligenceReport]:
        store = get_store()
        reports = store.list_all("intelligence")
        sorted_reports = sorted(
            reports,
            key=lambda r: r.get("generated_at", ""),
            reverse=True,
        )
        return [IntelligenceReport(**r) for r in sorted_reports[:limit]]
