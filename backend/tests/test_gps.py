import pytest

from app.engine.gps import check_gps, Verdict


@pytest.mark.asyncio
async def test_inside_region_passes():
    result = await check_gps("BATCH-A", 21.9731, 96.0836)
    assert result == Verdict.PASS


@pytest.mark.asyncio
async def test_outside_region_flags():
    result = await check_gps("BATCH-B", 21.9731, 96.0836)
    assert result == Verdict.FLAG


@pytest.mark.asyncio
async def test_unknown_batch_passes():
    result = await check_gps("BATCH-UNKNOWN", 0.0, 0.0)
    assert result == Verdict.PASS
