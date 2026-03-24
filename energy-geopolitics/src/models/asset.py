"""Energy asset data models for oil and gas infrastructure."""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
import uuid


class AssetType(str, Enum):
    OILFIELD = "oilfield"
    GAS_FIELD = "gas_field"
    PIPELINE = "pipeline"
    REFINERY = "refinery"
    LNG_TERMINAL = "lng_terminal"
    OFFSHORE_PLATFORM = "offshore_platform"
    STORAGE_FACILITY = "storage_facility"
    EXPORT_TERMINAL = "export_terminal"
    CHOKEPOINT = "chokepoint"


class AssetStatus(str, Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNDER_THREAT = "under_threat"
    SANCTIONED = "sanctioned"
    DECOMMISSIONED = "decommissioned"


class EnergyAsset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    asset_type: AssetType
    status: AssetStatus = AssetStatus.OPERATIONAL
    country: str
    region: str
    operator: str
    capacity_bpd: Optional[float] = None       # barrels per day
    current_output_bpd: Optional[float] = None
    capacity_mcfd: Optional[float] = None      # million cubic feet per day (gas)
    reserves_bbl: Optional[float] = None       # total proven reserves in barrels
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    strategic_importance: float = Field(default=0.5, ge=0.0, le=1.0)
    active_risk_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AssetCreate(BaseModel):
    name: str
    asset_type: AssetType
    country: str
    region: str
    operator: str
    capacity_bpd: Optional[float] = None
    current_output_bpd: Optional[float] = None
    capacity_mcfd: Optional[float] = None
    reserves_bbl: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    strategic_importance: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Dict[str, str] = Field(default_factory=dict)


class AssetUpdate(BaseModel):
    status: Optional[AssetStatus] = None
    current_output_bpd: Optional[float] = None
    strategic_importance: Optional[float] = None
