from fakeredis import FakeAsyncRedis
import pytest

from app.engine.orchestrator import evaluate_scan


@pytest.mark.asyncio
async def test_all_checks_pass_verified():
    redis = FakeAsyncRedis()
    result = await evaluate_scan(
        redis, "SERIAL-001", "BATCH-A", 21.9731, 96.0836,
        "2026-06-30T10:00:00", "consumer",
    )
    assert result.status == "verified"
    assert result.confidence == 1.0


@pytest.mark.asyncio
async def test_velocity_fail_flags():
    redis = FakeAsyncRedis()
    await redis.set("item:SERIAL-001:last_lat", "16.8661")
    await redis.set("item:SERIAL-001:last_lng", "96.1951")
    await redis.set("item:SERIAL-001:last_scan_ts", "2026-06-30T10:00:00")

    result = await evaluate_scan(
        redis, "SERIAL-001", "BATCH-A", 13.7563, 100.5018,
        "2026-06-30T10:45:00", "consumer",
    )
    assert result.status == "flagged"
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_density_prompt():
    redis = FakeAsyncRedis()
    await redis.set("item:SERIAL-001:scan_count", 3)

    result = await evaluate_scan(
        redis, "SERIAL-001", "BATCH-A", 21.9731, 96.0836,
        "2026-06-30T10:00:00", "consumer",
    )
    assert result.status == "prompt"
    assert result.confidence == 0.5
