import base64
import os

import cv2
from httpx import ASGITransport, AsyncClient
import pytest

from app.main import app

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_images")


def _image_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


@pytest.mark.asyncio
async def test_genuine_sample_verifies():
    path = os.path.join(SAMPLES_DIR, "genuine_BATCH-A_001.png")
    if not os.path.exists(path):
        pytest.skip("sample images not generated yet")
    b64 = _image_to_b64(path)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/verify",
            json={"batch_id": "BATCH-A", "serial": "001", "image_base64": b64},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "verified"


@pytest.mark.asyncio
async def test_tampered_sample_flags():
    path = os.path.join(SAMPLES_DIR, "tampered_BATCH-A_001.png")
    if not os.path.exists(path):
        pytest.skip("sample images not generated yet")
    b64 = _image_to_b64(path)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/verify",
            json={"batch_id": "BATCH-A", "serial": "001", "image_base64": b64},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "counterfeit"
    assert data["overlay_base64"] is not None
