import base64

import cv2
import numpy as np
from httpx import ASGITransport, AsyncClient
import pytest

from app.crypto.anchor import generate_anchor
from app.main import app


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_verify_returns_verified_for_valid_image():
    anchor = generate_anchor("BATCH-A:001")
    _, buf = cv2.imencode(".png", anchor)
    b64 = base64.b64encode(buf.tobytes()).decode()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/verify",
            json={"batch_id": "BATCH-A", "serial": "001", "image_base64": b64},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "verified"
    assert data["confidence"] >= 0.9
