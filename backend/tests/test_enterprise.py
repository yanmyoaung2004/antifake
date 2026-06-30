import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_create_api_key():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/enterprise/keys")
    assert resp.status_code == 201
    data = resp.json()
    assert data["api_key"].startswith("af_")


@pytest.mark.asyncio
async def test_create_batch_without_key_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/enterprise/batch",
            json={"batch_id": "BATCH-D", "serials": ["S1", "S2"], "region": "MYANMAR"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_batch_with_key_succeeds():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        key_resp = await client.post("/api/v1/enterprise/keys")
        api_key = key_resp.json()["api_key"]

        resp = await client.post(
            "/api/v1/enterprise/batch",
            json={"batch_id": "BATCH-D", "serials": ["S1", "S2"], "region": "MYANMAR"},
            headers={"X-API-Key": api_key},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["batch_id"] == "BATCH-D"
    assert data["count"] == 2
    assert data["region"] == "MYANMAR"
    assert data["layer1_qr"]
    assert data["layer2_pattern"]
