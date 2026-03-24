"""API integration tests using FastAPI TestClient."""
import pytest
from fastapi.testclient import TestClient
from src.main import create_app
from src.data.db import get_store, InMemoryStore
from src.data import seed


@pytest.fixture
def client():
    """Create a test client with fresh in-memory store and seed data."""
    import src.data.db as db_module
    db_module._store = InMemoryStore()
    seed.load_seed_data()

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_health_check(client):
    r = client.get("/api/v1/health/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"


def test_list_events(client):
    r = client.get("/api/v1/events/")
    assert r.status_code == 200
    events = r.json()
    assert isinstance(events, list)
    assert len(events) > 0


def test_events_summary(client):
    r = client.get("/api/v1/events/summary")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "by_severity" in data
    assert data["total"] > 0


def test_get_event_by_id(client):
    r = client.get("/api/v1/events/")
    events = r.json()
    first_id = events[0]["id"]
    r2 = client.get(f"/api/v1/events/{first_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == first_id


def test_get_event_not_found(client):
    r = client.get("/api/v1/events/nonexistent-id")
    assert r.status_code == 404


def test_create_event(client):
    payload = {
        "title": "Test Event via API",
        "description": "Created via test",
        "event_type": "conflict",
        "severity": "high",
        "country": "TestLand",
        "region": "Test Region",
    }
    r = client.post("/api/v1/events/", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == payload["title"]
    assert data["id"] is not None


def test_update_event_status(client):
    r = client.get("/api/v1/events/")
    event_id = r.json()[0]["id"]
    r2 = client.patch(f"/api/v1/events/{event_id}", json={"status": "resolved"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "resolved"


def test_list_assets(client):
    r = client.get("/api/v1/assets/")
    assert r.status_code == 200
    assets = r.json()
    assert len(assets) > 0


def test_list_chokepoints(client):
    r = client.get("/api/v1/assets/chokepoints")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_global_risk(client):
    r = client.get("/api/v1/intelligence/risk/global")
    assert r.status_code == 200
    data = r.json()
    assert "overall_score" in data
    assert "risk_level" in data
    assert 0.0 <= data["overall_score"] <= 1.0


def test_regional_risk(client):
    r = client.get("/api/v1/intelligence/risk/regional")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for region in data:
        assert "region" in region
        assert "risk_level" in region


def test_global_impact(client):
    r = client.get("/api/v1/intelligence/impact/global")
    assert r.status_code == 200
    data = r.json()
    assert "total_supply_at_risk_bpd" in data
    assert "pct_of_global_supply" in data


def test_generate_daily_brief(client):
    r = client.post("/api/v1/intelligence/reports/daily-brief")
    assert r.status_code == 201
    data = r.json()
    assert "title" in data
    assert "key_findings" in data
    assert len(data["key_findings"]) > 0


def test_list_alerts(client):
    # First run a scan to generate alerts
    client.post("/api/v1/intelligence/alerts/scan")
    r = client.get("/api/v1/intelligence/alerts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_filter_events_by_severity(client):
    r = client.get("/api/v1/events/?severity=critical")
    assert r.status_code == 200
    events = r.json()
    for e in events:
        assert e["severity"] == "critical"


def test_filter_assets_by_type(client):
    r = client.get("/api/v1/assets/?asset_type=chokepoint")
    assert r.status_code == 200
    assets = r.json()
    for a in assets:
        assert a["asset_type"] == "chokepoint"
