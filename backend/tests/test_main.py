import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_app_title():
    assert app.title == "AntiFake Backend"


@pytest.mark.asyncio
async def test_lifespan_skips_seed_when_disabled():
    os.environ["ANTIFAKE_SEED"] = "false"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
