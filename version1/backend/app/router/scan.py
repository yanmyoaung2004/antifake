from fastapi import APIRouter, Depends

from app.config import settings
from app.schemas import ScanRequest, ScanResponse
from app.engine.orchestrator import evaluate_scan
from app.dependencies import get_redis

router = APIRouter()


@router.post("/api/v1/scan", response_model=ScanResponse)
async def scan_product(body: ScanRequest, redis=Depends(get_redis)):
    lat = body.lat
    lng = body.lng

    if settings.mock_gps:
        parts = settings.mock_gps.split(",")
        if len(parts) == 2:
            lat = float(parts[0])
            lng = float(parts[1])

    result = await evaluate_scan(
        redis=redis,
        serial=body.serial,
        batch_id=body.batch_id,
        lat=lat,
        lng=lng,
        ts=body.timestamp,
        role=body.role,
        crypto_image=body.crypto_image,
    )
    return result
