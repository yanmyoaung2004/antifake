"""Tests the enhanced verify endpoint with batch lookup, scan tracking, velocity."""

import base64
import os

import cv2
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import init_db
from app.crypto.anchor import generate_anchor

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "sample_images")


def _b64(path: str) -> str:
    with open(os.path.join(SAMPLES, path), "rb") as f:
        return base64.b64encode(f.read()).decode()


def _make_anchor_b64(batch_id: str, serial: str) -> str:
    anchor = generate_anchor(f"{batch_id}:{serial}")
    _, buf = cv2.imencode(".png", anchor)
    return base64.b64encode(buf.tobytes()).decode()


@pytest.fixture(autouse=True)
async def setup_db():
    if os.path.exists("antifake.db"):
        os.remove("antifake.db")
    await init_db()
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from seed.seed_data import seed
    await seed()
    yield


@pytest.mark.asyncio
async def test_verify_returns_batch_info():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/verify", json={
            "batch_id": "BATCH-A",
            "serial": "001",
            "image_base64": _b64("genuine_BATCH-A_001.png"),
            "lat": 16.8661,
            "lng": 96.1951,
            "timestamp": "2026-07-06T10:00:00",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "verified"
    assert data["batch_info"] is not None
    assert data["batch_info"]["batch_id"] == "BATCH-A"
    assert data["batch_info"]["region"] == "MYANMAR"
    assert len(data["batch_info"]["route"]) == 4
    assert data["scan_history"]["scan_count"] == 1


@pytest.mark.asyncio
async def test_second_scan_shows_velocity_alert():
    """Two scans of same serial from different cities 30 min apart -> velocity alert."""
    transport = ASGITransport(app=app)
    b64 = _make_anchor_b64("BATCH-A", "VELOCITY-001")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i, (lat, lng, ts) in enumerate([
            (16.8661, 96.1951, "2026-07-06T10:00:00"),
            (21.9731, 96.0836, "2026-07-06T10:30:00"),
        ]):
            resp = await client.post("/api/v1/verify", json={
                "batch_id": "BATCH-A",
                "serial": "VELOCITY-001",
                "image_base64": b64,
                "lat": lat,
                "lng": lng,
                "timestamp": ts,
            })
            assert resp.status_code == 200
            data = resp.json()
            if i == 0:
                assert data["status"] == "verified"
                assert data["scan_history"]["scan_count"] == 1
            else:
                assert data["status"] == "flagged"
                assert data["scan_history"]["scan_count"] == 2
                assert data["scan_history"]["velocity_alert"] is not None
                assert "km" in data["scan_history"]["velocity_alert"]


@pytest.mark.asyncio
async def test_unknown_batch_returns_no_batch_info():
    """Batch not in registry -> batch_info is None, anchor still verified."""
    b64 = _make_anchor_b64("BATCH-UNKNOWN", "999")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/verify", json={
            "batch_id": "BATCH-UNKNOWN",
            "serial": "999",
            "image_base64": b64,
            "lat": 0,
            "lng": 0,
            "timestamp": "2026-07-06T10:00:00",
        })
    data = resp.json()
    assert data["status"] == "verified"
    assert data["batch_info"] is None
    assert data["scan_history"]["scan_count"] == 1


@pytest.mark.asyncio
async def test_counterfeit_still_returns_batch_info():
    """Counterfeit detection preserves batch info."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/verify", json={
            "batch_id": "BATCH-A",
            "serial": "003",
            "image_base64": _b64("tampered_BATCH-A_001.png"),
            "lat": 16.8661,
            "lng": 96.1951,
            "timestamp": "2026-07-06T10:00:00",
        })
    data = resp.json()
    assert data["status"] == "counterfeit"
    assert data["overlay_base64"] is not None
    assert data["batch_info"] is not None
    assert data["batch_info"]["batch_id"] == "BATCH-A"
