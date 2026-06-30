import pytest


@pytest.mark.asyncio
async def test_scan_endpoint_returns_200(test_client):
    payload = {
        "serial": "SERIAL-001",
        "batch_id": "BATCH-A",
        "lat": 21.9731,
        "lng": 96.0836,
        "timestamp": "2026-06-30T10:00:00",
        "role": "consumer",
    }
    async with test_client as client:
        resp = await client.post("/api/v1/scan", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("verified", "flagged", "prompt", "error")
    assert "confidence" in data
    assert "message" in data


@pytest.mark.asyncio
async def test_health_endpoint(test_client):
    async with test_client as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
