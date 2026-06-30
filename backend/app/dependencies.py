from fakeredis import FakeAsyncRedis
from redis.asyncio import Redis

from app.config import settings

_redis_instance: Redis | None = None
_fake_redis: FakeAsyncRedis | None = None


async def get_redis() -> Redis:
    global _redis_instance, _fake_redis

    if settings.redis_url == "fakeredis":
        if _fake_redis is None:
            _fake_redis = FakeAsyncRedis()
        return _fake_redis

    if _redis_instance is None:
        _redis_instance = Redis.from_url(settings.redis_url)
    return _redis_instance
