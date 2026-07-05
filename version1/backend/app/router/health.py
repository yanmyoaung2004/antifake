from fastapi import APIRouter, Depends

from app.blockchain.client import blockchain_client
from app.dependencies import get_redis

router = APIRouter()


@router.get("/api/v1/health")
async def health(redis=Depends(get_redis)):
    redis_ok = False
    try:
        await redis.ping()
        redis_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if redis_ok else "degraded",
        "redis": redis_ok,
        "rpc": blockchain_client.is_connected,
    }
