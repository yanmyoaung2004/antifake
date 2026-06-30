import os

import pytest
import httpx

E2E_BASE = os.environ.get("ANTIFAKE_E2E_URL", "http://localhost:8000")
RUN_E2E = os.environ.get("ANTIFAKE_E2E", "").lower() in ("1", "true")

pytestmark = pytest.mark.skipif(not RUN_E2E, reason="set ANTIFAKE_E2E=1 to run e2e tests")


@pytest.fixture
def client():
    return httpx.Client(base_url=E2E_BASE, timeout=30)


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")


def test_scan_verified(client):
    payload = {
        "serial": "BATCH-A-0001",
        "batch_id": "BATCH-A",
        "lat": 21.9731,
        "lng": 96.0836,
        "timestamp": "2026-06-30T10:00:00",
        "role": "consumer",
    }
    resp = client.post("/api/v1/scan", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] in ("verified", "prompt")


def test_scan_flagged_gps(client):
    payload = {
        "serial": "BATCH-A-0002",
        "batch_id": "BATCH-B",
        "lat": 21.9731,
        "lng": 96.0836,
        "timestamp": "2026-06-30T10:00:00",
        "role": "consumer",
    }
    resp = client.post("/api/v1/scan", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "flagged"


def test_scan_density_prompts(client):
    serial = "BATCH-A-0003"
    for i in range(4):
        payload = {
            "serial": serial,
            "batch_id": "BATCH-A",
            "lat": 21.9731,
            "lng": 96.0836,
            "timestamp": "2026-06-30T10:00:00",
            "role": "consumer",
        }
        resp = client.post("/api/v1/scan", json=payload)
        assert resp.status_code == 200
        if i < 3:
            assert resp.json()["status"] in ("verified", "prompt")
        else:
            assert resp.json()["status"] == "prompt"
