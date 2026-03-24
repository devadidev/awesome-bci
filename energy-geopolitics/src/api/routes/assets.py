"""Energy assets API routes."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from src.models import EnergyAsset, AssetType, AssetStatus
from src.models.asset import AssetCreate, AssetUpdate
from src.data.db import get_store
from src.analysis.impact_analyzer import ImpactAnalyzer
from src.logger import get_logger

router = APIRouter(prefix="/assets", tags=["Assets"])
logger = get_logger(__name__)
analyzer = ImpactAnalyzer()


@router.get("/", response_model=List[EnergyAsset])
async def list_assets(
    asset_type: Optional[AssetType] = Query(None),
    status: Optional[AssetStatus] = Query(None),
    country: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    min_importance: float = Query(0.0, ge=0.0, le=1.0),
):
    store = get_store()
    assets = store.list_all("assets")

    if asset_type:
        assets = [a for a in assets if a.get("asset_type") == asset_type]
    if status:
        assets = [a for a in assets if a.get("status") == status]
    if country:
        assets = [a for a in assets if country.lower() in (a.get("country") or "").lower()]
    if region:
        assets = [a for a in assets if region.lower() in (a.get("region") or "").lower()]
    if min_importance > 0:
        assets = [a for a in assets if a.get("strategic_importance", 0) >= min_importance]

    assets = sorted(assets, key=lambda a: a.get("strategic_importance", 0), reverse=True)
    return [EnergyAsset(**a) for a in assets]


@router.get("/chokepoints")
async def list_chokepoints():
    """Get all strategic chokepoints with risk exposure."""
    return analyzer.chokepoint_risk()


@router.get("/{asset_id}", response_model=EnergyAsset)
async def get_asset(asset_id: str):
    store = get_store()
    asset = store.get("assets", asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return EnergyAsset(**asset)


@router.get("/{asset_id}/exposure")
async def get_asset_exposure(asset_id: str):
    """Get supply chain exposure analysis for a specific asset."""
    exposure = analyzer.asset_exposure(asset_id)
    if not exposure:
        raise HTTPException(status_code=404, detail="Asset not found")
    return exposure


@router.post("/", response_model=EnergyAsset, status_code=201)
async def create_asset(payload: AssetCreate):
    store = get_store()
    asset = EnergyAsset(**payload.model_dump())
    store.insert("assets", asset.model_dump())
    logger.info("asset_created", asset_id=asset.id, name=asset.name)
    return asset


@router.patch("/{asset_id}", response_model=EnergyAsset)
async def update_asset(asset_id: str, payload: AssetUpdate):
    store = get_store()
    updated = store.update("assets", asset_id, payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Asset not found")
    return EnergyAsset(**updated)
