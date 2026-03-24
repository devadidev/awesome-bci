"""Geopolitical events API routes."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from src.models import GeopoliticalEvent, EventType, EventSeverity, EventStatus
from src.models.event import EventCreate, EventUpdate
from src.data.db import get_store
from src.analysis.alert_engine import AlertEngine
from src.logger import get_logger

router = APIRouter(prefix="/events", tags=["Events"])
logger = get_logger(__name__)
alert_engine = AlertEngine()


@router.get("/", response_model=List[GeopoliticalEvent])
async def list_events(
    status: Optional[EventStatus] = Query(None),
    severity: Optional[EventSeverity] = Query(None),
    event_type: Optional[EventType] = Query(None),
    country: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    store = get_store()
    events = store.list_all("events")

    if status:
        events = [e for e in events if e.get("status") == status]
    if severity:
        events = [e for e in events if e.get("severity") == severity]
    if event_type:
        events = [e for e in events if e.get("event_type") == event_type]
    if country:
        events = [e for e in events if country.lower() in (e.get("country") or "").lower()]
    if region:
        events = [e for e in events if region.lower() in (e.get("region") or "").lower()]

    events = sorted(events, key=lambda e: e.get("detected_at", ""), reverse=True)
    return [GeopoliticalEvent(**e) for e in events[:limit]]


@router.get("/summary")
async def events_summary():
    store = get_store()
    events = store.list_all("events")
    by_severity = {}
    by_type = {}
    by_status = {}
    for e in events:
        by_severity[e.get("severity")] = by_severity.get(e.get("severity"), 0) + 1
        by_type[e.get("event_type")] = by_type.get(e.get("event_type"), 0) + 1
        by_status[e.get("status")] = by_status.get(e.get("status"), 0) + 1

    return {
        "total": len(events),
        "by_severity": by_severity,
        "by_type": by_type,
        "by_status": by_status,
        "active": by_status.get("active", 0) + by_status.get("monitoring", 0) + by_status.get("escalating", 0),
    }


@router.get("/{event_id}", response_model=GeopoliticalEvent)
async def get_event(event_id: str):
    store = get_store()
    event = store.get("events", event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return GeopoliticalEvent(**event)


@router.post("/", response_model=GeopoliticalEvent, status_code=201)
async def create_event(payload: EventCreate):
    store = get_store()
    event = GeopoliticalEvent(**payload.model_dump())
    store.insert("events", event.model_dump())

    # Auto-generate alert if warranted
    alert = alert_engine.evaluate_event(event)
    if alert:
        store.insert("alerts", alert.model_dump())
        logger.info("auto_alert_created", alert_id=alert.id, event_id=event.id)

    logger.info("event_created", event_id=event.id, title=event.title)
    return event


@router.patch("/{event_id}", response_model=GeopoliticalEvent)
async def update_event(event_id: str, payload: EventUpdate):
    store = get_store()
    updated = store.update("events", event_id, payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Event not found")
    return GeopoliticalEvent(**updated)


@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: str):
    store = get_store()
    if not store.delete("events", event_id):
        raise HTTPException(status_code=404, detail="Event not found")
