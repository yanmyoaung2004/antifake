"""
Tests for the AI Pharmacist explanation engine.
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
async def test_explain_returns_initial_reply():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/explain",
            json={
                "verify_response": {
                    "status": "verified",
                    "confidence": 0.95,
                    "batch_info": {"drug_name": "Test", "region": "MYANMAR", "route": []},
                    "scan_history": {"scan_count": 1},
                    "ai_confidence": {"p_genuine": 0.98, "p_counterfeit": 0.02, "model": "resnet18", "model_agrees_with_cv": True},
                }
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert len(data["reply"]) > 20
    assert len(data["suggestions"]) > 0


@pytest.mark.asyncio
async def test_explain_followup():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/explain",
            json={
                "verify_response": {"status": "counterfeit", "confidence": 0.3, "metrics": {"edge_ratio": 0.45}},
                "user_message": "What does edge sharpness mean?",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "edge" in data["reply"].lower() or "sharpness" in data["reply"].lower()


@pytest.mark.asyncio
async def test_explain_with_velocity_alert():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/explain",
            json={
                "verify_response": {
                    "status": "flagged",
                    "confidence": 0.3,
                    "scan_history": {
                        "scan_count": 2,
                        "velocity_alert": "Impossible movement detected — 570 km in 60 min.",
                        "previous_scan": {"lat": 16.86, "lng": 96.19, "timestamp": "2026-07-09T10:00:00", "result": "verified"},
                    },
                }
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "velocity" in data["reply"].lower() or "movement" in data["reply"].lower()
