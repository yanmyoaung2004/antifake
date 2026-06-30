import math
from datetime import datetime

from app.config import settings


class Verdict:
    PASS = "pass"
    FLAG = "flag"


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def check_velocity(
    redis, serial: str, lat: float, lng: float, ts: str
) -> str:
    last_lat = await redis.get(f"item:{serial}:last_lat")
    if last_lat is None:
        return Verdict.PASS

    last_lng = await redis.get(f"item:{serial}:last_lng")
    last_ts = await redis.get(f"item:{serial}:last_scan_ts")

    if last_lng is None or last_ts is None:
        return Verdict.PASS

    prev_lat = float(last_lat)
    prev_lng = float(last_lng)
    prev_ts = datetime.fromisoformat(last_ts.decode())
    curr_ts = datetime.fromisoformat(ts)

    distance = haversine_km(prev_lat, prev_lng, lat, lng)
    hours = (curr_ts - prev_ts).total_seconds() / 3600.0

    if hours <= 0:
        return Verdict.PASS

    speed = distance / hours
    if speed > settings.velocity_max_kmh:
        return Verdict.FLAG

    return Verdict.PASS
