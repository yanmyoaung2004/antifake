import asyncio
from datetime import datetime, timezone

from app.engine.velocity import check_velocity, Verdict as VelocityVerdict
from app.engine.density import check_density, Verdict as DensityVerdict
from app.engine.gps import check_gps, Verdict as GpsVerdict
from app.crypto.anchor import verify_anchor
from app.schemas import ScanResponse


async def evaluate_scan(
    redis,
    serial: str,
    batch_id: str,
    lat: float,
    lng: float,
    ts: str,
    role: str,
    crypto_image: str | None = None,
) -> ScanResponse:
    velocity_task = check_velocity(redis, serial, lat, lng, ts)
    density_task = check_density(redis, serial, role)
    gps_task = check_gps(batch_id, lat, lng)

    anchor_task = None
    if crypto_image is not None:
        anchor_task = verify_anchor(crypto_image)

    results = await asyncio.gather(velocity_task, density_task, gps_task)
    vel, den, gps = results

    anchor_result = None
    if anchor_task is not None:
        anchor_result = await anchor_task

    now = datetime.now(timezone.utc).isoformat()

    for label, result in [("velocity", vel), ("gps", gps)]:
        if result in (VelocityVerdict.FLAG, GpsVerdict.FLAG):
            return ScanResponse(
                status="flagged",
                confidence=0.0,
                message=f"Spatial-temporal anomaly detected ({label} check failed).",
                last_verified=now,
            )

    if anchor_result is not None and anchor_result.get("degraded"):
        return ScanResponse(
            status="flagged",
            confidence=0.0,
            message="Crypto-anchor appears degraded. Likely counterfeit.",
            last_verified=now,
        )

    if den == DensityVerdict.FLAG_PROMPT:
        return ScanResponse(
            status="prompt",
            confidence=0.5,
            message="This code has been scanned before. Report counterfeits or verify authenticity?",
            last_verified=now,
        )

    await redis.set(f"item:{serial}:last_lat", lat)
    await redis.set(f"item:{serial}:last_lng", lng)
    await redis.set(f"item:{serial}:last_scan_ts", ts)

    return ScanResponse(
        status="verified",
        confidence=1.0,
        message="Product verified. Authentic.",
        last_verified=now,
    )
