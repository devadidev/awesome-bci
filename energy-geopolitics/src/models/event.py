"""Geopolitical event data models."""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


class EventType(str, Enum):
    CONFLICT = "conflict"
    SANCTIONS = "sanctions"
    POLICY_CHANGE = "policy_change"
    SUPPLY_DISRUPTION = "supply_disruption"
    PIPELINE_INCIDENT = "pipeline_incident"
    NATURAL_DISASTER = "natural_disaster"
    POLITICAL_INSTABILITY = "political_instability"
    TRADE_DISPUTE = "trade_dispute"
    CARTEL_DECISION = "cartel_decision"
    INFRASTRUCTURE_ATTACK = "infrastructure_attack"


class EventSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class EventStatus(str, Enum):
    ACTIVE = "active"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    ESCALATING = "escalating"


class GeopoliticalEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    event_type: EventType
    severity: EventSeverity
    status: EventStatus = EventStatus.MONITORING
    country: str
    region: str
    affected_assets: List[str] = Field(default_factory=list)
    supply_impact_bpd: Optional[float] = None  # barrels per day affected
    price_impact_pct: Optional[float] = None   # estimated % price impact
    source: str = "manual"
    source_url: Optional[str] = None
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EventCreate(BaseModel):
    title: str
    description: str
    event_type: EventType
    severity: EventSeverity
    country: str
    region: str
    affected_assets: List[str] = Field(default_factory=list)
    supply_impact_bpd: Optional[float] = None
    price_impact_pct: Optional[float] = None
    source: str = "manual"
    source_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class EventUpdate(BaseModel):
    status: Optional[EventStatus] = None
    severity: Optional[EventSeverity] = None
    supply_impact_bpd: Optional[float] = None
    price_impact_pct: Optional[float] = None
    resolved_at: Optional[datetime] = None
    tags: Optional[List[str]] = None
