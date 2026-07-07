import base64
import math
import os
from datetime import datetime, timezone

import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.crypto.anchor import generate_anchor, extract_noise, compare_anchors, compute_overlay
from app.database import init_db, get_batch, get_route, get_scan_history, record_scan
from app.models import VerifyRequest, VerifyResponse, RoutePoint, BatchInfo, PreviousScan, ScanHistory

VELOCITY_MAX_KMH = 120.0

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="AntiFake v2", lifespan=lifespan)


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


def build_velocity_alert(prev_scan: dict, lat: float, lng: float, ts: str) -> str | None:
    prev_lat = prev_scan["lat"]
    prev_lng = prev_scan["lng"]
    prev_ts = prev_scan["timestamp"]
    try:
        distance = haversine_km(prev_lat, prev_lng, lat, lng)
        prev_dt = datetime.fromisoformat(prev_ts)
        curr_dt = datetime.fromisoformat(ts)
        hours = (curr_dt - prev_dt).total_seconds() / 3600.0
        if hours <= 0:
            return None
        speed = distance / hours
        if speed > VELOCITY_MAX_KMH:
            return (
                f"⚠ Impossible movement detected — {distance:.0f} km in "
                f"{hours * 60:.0f} min ({speed:.0f} km/h). "
                f"Previous scan was at ({prev_lat:.1f}, {prev_lng:.1f})."
            )
    except Exception:
        pass
    return None


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/verify", response_model=VerifyResponse)
async def verify(body: VerifyRequest):
    try:
        ts = body.timestamp or datetime.now(timezone.utc).isoformat()

        raw = base64.b64decode(body.image_base64)
        arr = np.frombuffer(raw, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return VerifyResponse(
                status="error", confidence=0.0, message="Could not decode image."
            )

        seed = f"{body.batch_id}:{body.serial}"
        expected = generate_anchor(seed)
        actual = extract_noise(img)

        anchor_result = compare_anchors(expected, actual)

        overlay_b64 = None
        if anchor_result["degraded"]:
            heatmap = compute_overlay(actual, expected)
            _, buf = cv2.imencode(".png", heatmap)
            overlay_b64 = base64.b64encode(buf.tobytes()).decode()

        anchor_degraded = anchor_result["degraded"]
        status = "counterfeit" if anchor_degraded else "verified"
        message = (
            "Print quality deviation detected. Likely counterfeit."
            if anchor_degraded
            else "Anchor pattern matches. Authentic."
        )

        batch_info = None
        batch_row = await get_batch(body.batch_id)
        if batch_row:
            route_rows = await get_route(body.batch_id)
            route = [
                RoutePoint(
                    location_name=r["location_name"],
                    lat=r["lat"],
                    lng=r["lng"],
                    event=r["event"],
                )
                for r in route_rows
            ]
            batch_info = BatchInfo(
                batch_id=batch_row["batch_id"],
                region=batch_row["region"],
                mint_date=batch_row["mint_date"],
                route=route,
            )

        history = await get_scan_history(body.serial)
        scan_count = len(history)
        velocity_alert = None
        previous_scan = None

        if scan_count > 0 and not anchor_degraded:
            latest = history[0]
            previous_scan = PreviousScan(
                lat=latest["lat"],
                lng=latest["lng"],
                timestamp=latest["timestamp"],
                result=latest["result"],
            )
            velocity_alert = build_velocity_alert(
                latest, body.lat, body.lng, ts
            )

        scan_history = ScanHistory(
            scan_count=scan_count + 1,
            velocity_alert=velocity_alert,
            previous_scan=previous_scan,
        )

        await record_scan(
            serial=body.serial,
            batch_id=body.batch_id,
            lat=body.lat,
            lng=body.lng,
            timestamp=ts,
            result=status,
        )

        return VerifyResponse(
            status=status,
            confidence=anchor_result["confidence"],
            message=message,
            metrics=anchor_result if anchor_degraded else anchor_result,
            overlay_base64=overlay_b64,
            batch_info=batch_info,
            scan_history=scan_history,
        )

    except Exception as e:
        return VerifyResponse(
            status="error", confidence=0.0, message=f"Verification failed: {str(e)}"
        )


web_dir = os.path.join(os.path.dirname(__file__), "..", "..", "web")
if os.path.isdir(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
