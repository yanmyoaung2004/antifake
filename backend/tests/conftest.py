import pytest
from fakeredis import FakeAsyncRedis
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.dependencies import get_redis


@pytest.fixture
def fake_redis():
    return FakeAsyncRedis()


@pytest.fixture
def test_client(fake_redis):
    async def override_get_redis():
        return fake_redis

    app.dependency_overrides[get_redis] = override_get_redis
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    app.dependency_overrides.clear()
