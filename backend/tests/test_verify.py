import base64
import os

import cv2
import numpy as np
from httpx import ASGITransport, AsyncClient
import pytest

from app.crypto.anchor import generate_anchor
from app.main import app
from app.database import init_db


@pytest.fixture(autouse=True)
async def setup_db():
    if os.path.exists("antifake.db"):
        os.remove("antifake.db")
    await init_db()
    yield


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_verify_returns_verified_for_valid_image():
    anchor = generate_anchor("BATCH-A:T001")
    _, buf = cv2.imencode(".png", anchor)
    b64 = base64.b64encode(buf.tobytes()).decode()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/verify",
            json={"batch_id": "BATCH-A", "serial": "T001", "image_base64": b64, "lat": 21.0, "lng": 96.0, "timestamp": "2026-07-07T10:00:00"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "verified"
    assert data["confidence"] >= 0.9
