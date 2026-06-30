from fakeredis import FakeAsyncRedis
import pytest

from app.engine.density import check_density, Verdict


@pytest.mark.asyncio
async def test_consumer_first_scan_passes():
    redis = FakeAsyncRedis()
    result = await check_density(redis, "SERIAL-001", "consumer")
    assert result == Verdict.PASS


@pytest.mark.asyncio
async def test_consumer_fourth_scan_prompts():
    redis = FakeAsyncRedis()
    await redis.set("item:SERIAL-001:scan_count", 3)
    result = await check_density(redis, "SERIAL-001", "consumer")
    assert result == Verdict.FLAG_PROMPT


@pytest.mark.asyncio
async def test_wholesaler_never_flags():
    redis = FakeAsyncRedis()
    await redis.set("item:SERIAL-001:scan_count", 1000)
    result = await check_density(redis, "SERIAL-001", "wholesaler")
    assert result == Verdict.PASS
