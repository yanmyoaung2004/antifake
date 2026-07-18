import asyncio
import base64
import os

import cv2
import numpy as np
from httpx import ASGITransport, AsyncClient
import pytest

from app.crypto.anchor import generate_anchor, simulate_photocopy
from app.database import init_db
from app.main import app

# Initialize DB at module level
asyncio.run(init_db())


def _anchor_to_b64(anchor: np.ndarray) -> str:
    _, buf = cv2.imencode(".png", anchor)
    return base64.b64encode(buf.tobytes()).decode()


@pytest.mark.asyncio
async def test_genuine_sample_verifies():
    anchor = generate_anchor("BATCH-A:SMPL-VRFY")
    b64 = _anchor_to_b64(anchor)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/verify",
            json={"batch_id": "BATCH-A", "serial": "SMPL-VRFY", "image_base64": b64, "lat": 21.0, "lng": 96.0, "timestamp": "2026-07-07T10:00:00"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "verified"


@pytest.mark.asyncio
async def test_tampered_sample_flags():
    anchor = generate_anchor("BATCH-A:SMPL-FAKE")
    tampered = simulate_photocopy(anchor, severity=0.35)
    b64 = _anchor_to_b64(tampered)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/verify",
            json={"batch_id": "BATCH-A", "serial": "SMPL-FAKE", "image_base64": b64, "lat": 21.0, "lng": 96.0, "timestamp": "2026-07-07T10:00:00"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "counterfeit"
    assert data["overlay_base64"] is not None
