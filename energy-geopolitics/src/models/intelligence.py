"""Intelligence report and alert models."""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
import uuid


class ReportType(str, Enum):
    DAILY_BRIEF = "daily_brief"
    SITUATIONAL_AWARENESS = "situational_awareness"
    RISK_ASSESSMENT = "risk_assessment"
    SUPPLY_DISRUPTION = "supply_disruption"
    MARKET_IMPACT = "market_impact"
    SANCTIONS_UPDATE = "sanctions_update"
    INFRASTRUCTURE_THREAT = "infrastructure_threat"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class OilPriceSnapshot(BaseModel):
    timestamp: datetime
    brent_crude_usd: Optional[float] = None
    wti_crude_usd: Optional[float] = None
    natural_gas_usd: Optional[float] = None
    change_24h_pct: Optional[float] = None
    source: str = "simulated"

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class IntelligenceReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    report_type: ReportType
    summary: str
    full_content: str
    key_findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    referenced_event_ids: List[str] = Field(default_factory=list)
    referenced_asset_ids: List[str] = Field(default_factory=list)
    risk_assessment_ids: List[str] = Field(default_factory=list)

    price_snapshot: Optional[OilPriceSnapshot] = None
    regions_covered: List[str] = Field(default_factory=list)
    threat_actors: List[str] = Field(default_factory=list)

    confidence_level: float = Field(default=0.8, ge=0.0, le=1.0)
    classification: str = "UNCLASSIFIED"
    generated_by: str = "ai_engine"
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AlertNotification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    message: str
    severity: AlertSeverity
    event_id: Optional[str] = None
    asset_id: Optional[str] = None
    risk_score: Optional[float] = None
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    metadata: Dict[str, str] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
