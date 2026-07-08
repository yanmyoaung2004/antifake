"""
Tests for the partnership API: /api/v1/register and /api/v1/batches.
"""
import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import init_db


@pytest.fixture(autouse=True)
async def setup_db():
    if os.path.exists("antifake.db"):
        os.remove("antifake.db")
    await init_db()
    yield


@pytest.mark.asyncio
async def test_register_new_batch():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/register",
            json={
                "batch_id": "TEST-001",
                "region": "MYANMAR",
                "mint_date": "2026-07-01",
                "manufacturer": "Test Pharma Co.",
                "drug_name": "Test Drug 500mg",
                "drug_use": "Headache Relief",
                "expiry": "2028-07",
                "route": [
                    {"location_name": "Factory", "lat": 16.8661, "lng": 96.1951, "event": "Manufactured"},
                    {"location_name": "Pharmacy", "lat": 16.8500, "lng": 96.2000, "event": "Delivered"},
                ],
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted"] is True
    assert data["batch_id"] == "TEST-001"


@pytest.mark.asyncio
async def test_register_idempotent_update():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First call: insert
        await client.post(
            "/api/v1/register",
            json={"batch_id": "TEST-002", "region": "MYANMAR", "mint_date": "2026-07-01", "drug_name": "v1"},
        )
        # Second call: update
        resp = await client.post(
            "/api/v1/register",
            json={"batch_id": "TEST-002", "region": "MYANMAR", "mint_date": "2026-07-01", "drug_name": "v2"},
        )
    data = resp.json()
    assert data["inserted"] is False
    assert data["message"] == "Batch updated"


@pytest.mark.asyncio
async def test_list_batches():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i in range(3):
            await client.post(
                "/api/v1/register",
                json={
                    "batch_id": f"LIST-{i:03d}",
                    "region": "MYANMAR",
                    "mint_date": "2026-07-01",
                },
            )
        resp = await client.get("/api/v1/batches")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    ids = sorted(b["batch_id"] for b in data["batches"])
    assert ids == ["LIST-000", "LIST-001", "LIST-002"]


@pytest.mark.asyncio
async def test_register_replaces_route():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/register",
            json={
                "batch_id": "ROUTE-TEST",
                "region": "MYANMAR",
                "mint_date": "2026-07-01",
                "route": [
                    {"location_name": "A", "lat": 16.0, "lng": 96.0, "event": "Manufactured"},
                    {"location_name": "B", "lat": 16.1, "lng": 96.1, "event": "Delivered"},
                ],
            },
        )
        # Re-register with different route
        await client.post(
            "/api/v1/register",
            json={
                "batch_id": "ROUTE-TEST",
                "region": "MYANMAR",
                "mint_date": "2026-07-01",
                "route": [
                    {"location_name": "X", "lat": 17.0, "lng": 97.0, "event": "Manufactured"},
                ],
            },
        )
        resp = await client.get("/api/v1/batches")
    batches = resp.json()["batches"]
    target = [b for b in batches if b["batch_id"] == "ROUTE-TEST"][0]
    assert len(target["route"]) == 1
    assert target["route"][0]["location_name"] == "X"


@pytest.mark.asyncio
async def test_register_rejects_missing_required():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/register",
            json={"batch_id": "TEST-INVALID"},  # missing region and mint_date
        )
    # Pydantic returns 422 for missing required fields
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_registered_batch_appears_in_verify():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/register",
            json={
                "batch_id": "VERIFY-TEST",
                "region": "MYANMAR",
                "mint_date": "2026-07-01",
                "manufacturer": "MMR Pharma",
                "drug_name": "Test 100mg",
                "drug_use": "Test use",
                "expiry": "2028-01",
                "route": [
                    {"location_name": "Factory", "lat": 16.8661, "lng": 96.1951, "event": "Manufactured"},
                ],
            },
        )
        resp = await client.post(
            "/api/v1/verify",
            json={"batch_id": "VERIFY-TEST", "serial": "X1", "lat": 16.8661, "lng": 96.1951, "timestamp": "2026-07-09T00:00:00"},
        )
    data = resp.json()
    assert data["batch_info"] is not None
    assert data["batch_info"]["manufacturer"] == "MMR Pharma"
    assert data["batch_info"]["drug_name"] == "Test 100mg"
