import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.router import scan, health, enterprise


def _run_seed():
    try:
        from seed.seed import main as seed_main
        seed_main()
    except ImportError:
        pass
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("ANTIFAKE_SEED", "true").lower() == "true":
        _run_seed()
    yield


app = FastAPI(title="AntiFake Backend", lifespan=lifespan)
app.include_router(scan.router)
app.include_router(health.router)
app.include_router(enterprise.router)
