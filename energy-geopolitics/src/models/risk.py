"""Risk assessment models for energy geopolitics."""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
import uuid


class RiskLevel(str, Enum):
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class RiskFactor(BaseModel):
    name: str
    score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    description: str
    contributing_event_ids: List[str] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: Optional[str] = None    # None = global/regional assessment
    country: Optional[str] = None
    region: Optional[str] = None

    overall_score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel

    # Dimensional risk scores
    geopolitical_score: float = Field(ge=0.0, le=1.0)
    supply_disruption_score: float = Field(ge=0.0, le=1.0)
    infrastructure_score: float = Field(ge=0.0, le=1.0)
    sanctions_score: float = Field(ge=0.0, le=1.0)
    market_volatility_score: float = Field(ge=0.0, le=1.0)

    risk_factors: List[RiskFactor] = Field(default_factory=list)

    # Supply chain impact
    estimated_supply_at_risk_bpd: Optional[float] = None
    estimated_price_impact_range: Optional[Dict[str, float]] = None  # {"low": 2.0, "high": 8.5}

    # Forecast
    trend: str = "stable"  # improving, stable, deteriorating
    forecast_30d: Optional[float] = None
    forecast_90d: Optional[float] = None

    contributing_event_ids: List[str] = Field(default_factory=list)
    assessed_at: datetime = Field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = None
    analyst_notes: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class RegionalRiskSummary(BaseModel):
    region: str
    countries: List[str]
    avg_risk_score: float
    risk_level: RiskLevel
    active_events: int
    assets_at_risk: int
    total_supply_at_risk_bpd: float
    last_updated: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
