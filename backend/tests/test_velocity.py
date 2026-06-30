from fakeredis import FakeAsyncRedis
import pytest

from app.engine.velocity import check_velocity, Verdict

YANGON = (16.8661, 96.1951)
BANGKOK = (13.7563, 100.5018)


@pytest.mark.asyncio
async def test_no_prior_scan_passes():
    redis = FakeAsyncRedis()
    result = await check_velocity(redis, "SERIAL-001", *YANGON, "2026-06-30T10:00:00")
    assert result == Verdict.PASS


@pytest.mark.asyncio
async def test_impossible_speed_flags():
    redis = FakeAsyncRedis()
    await redis.set("item:SERIAL-001:last_lat", str(YANGON[0]))
    await redis.set("item:SERIAL-001:last_lng", str(YANGON[1]))
    await redis.set("item:SERIAL-001:last_scan_ts", "2026-06-30T10:00:00")

    result = await check_velocity(
        redis, "SERIAL-001", *BANGKOK, "2026-06-30T10:45:00"
    )
    assert result == Verdict.FLAG


@pytest.mark.asyncio
async def test_plausible_speed_passes():
    redis = FakeAsyncRedis()
    await redis.set("item:SERIAL-001:last_lat", str(YANGON[0]))
    await redis.set("item:SERIAL-001:last_lng", str(YANGON[1]))
    await redis.set("item:SERIAL-001:last_scan_ts", "2026-06-30T10:00:00")

    result = await check_velocity(
        redis, "SERIAL-001", *BANGKOK, "2026-06-30T18:00:00"
    )
    assert result == Verdict.PASS
