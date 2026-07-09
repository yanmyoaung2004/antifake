import base64
import math
import os
from datetime import datetime, timezone

import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.crypto.anchor import generate_anchor, compare_anchors, compute_overlay
from app.crypto.preprocess import preprocess_photo
from app.ml.classifier import predict_proba, is_available as ml_available
from app.database import (
    init_db,
    get_batch,
    get_route,
    get_scan_history,
    get_scan_count,
    record_scan,
    verify_chain,
    upsert_batch,
    clear_route,
    add_route_point,
    list_batches,
)
from app.models import (
    VerifyRequest,
    VerifyResponse,
    RoutePoint,
    BatchInfo,
    PreviousScan,
    ScanHistory,
    RegisterBatchRequest,
    RegisterBatchResponse,
    ListBatchesResponse,
    AIConfidence,
    ExplainRequest,
    ExplainResponse,
)

VELOCITY_MAX_KMH = 120.0
DENSITY_THRESHOLD = 2
ANCHOR_SIZE_FALLBACK = 64

REGION_BOUNDS = {
    "MYANMAR": {"min_lat": 10.0, "max_lat": 28.5, "min_lng": 92.0, "max_lng": 101.0},
    "VIETNAM": {"min_lat": 8.5, "max_lat": 23.5, "min_lng": 102.0, "max_lng": 110.0},
    "THAILAND": {"min_lat": 5.5, "max_lat": 20.5, "min_lng": 97.0, "max_lng": 106.0},
}


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
    try:
        distance = haversine_km(prev_scan["lat"], prev_scan["lng"], lat, lng)
        prev_dt = datetime.fromisoformat(prev_scan["timestamp"])
        curr_dt = datetime.fromisoformat(ts)
        hours = (curr_dt - prev_dt).total_seconds() / 3600.0
        if hours <= 0:
            return None
        speed = distance / hours
        if speed > VELOCITY_MAX_KMH:
            return (
                f"Impossible movement detected — {distance:.0f} km in "
                f"{hours * 60:.0f} min ({speed:.0f} km/h). "
                f"Previous scan was at ({prev_scan['lat']:.1f}, {prev_scan['lng']:.1f})."
            )
    except Exception:
        pass
    return None


def gps_in_region(lat: float, lng: float, region: str) -> bool:
    bounds = REGION_BOUNDS.get(region)
    if not bounds:
        return True
    return bounds["min_lat"] <= lat <= bounds["max_lat"] and bounds["min_lng"] <= lng <= bounds["max_lng"]


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/model/info")
async def model_info():
    """Whether the AI classifier is loaded and ready."""
    from app.ml.classifier import model_path, load_error
    return {
        "ml_available": ml_available(),
        "model_path": model_path(),
        "load_error": load_error(),
    }


@app.post("/api/v1/explain", response_model=ExplainResponse)
async def explain(body: ExplainRequest):
    """Generate a natural-language explanation of a verification result."""
    from app.ml.explainer import generate_explanation
    result = generate_explanation(
        verify=body.verify_response,
        user_message=body.user_message,
        conversation=body.conversation,
    )
    return ExplainResponse(
        reply=result.get("reply", "No explanation available."),
        suggestions=result.get("suggestions", []),
    )


@app.post("/api/v1/verify", response_model=VerifyResponse)
async def verify(body: VerifyRequest):
    try:
        ts = body.timestamp or datetime.now(timezone.utc).isoformat()
        alerts = []
        anchor_result = None
        overlay_b64 = None
        metrics = None
        ai_conf = None

        # --- Optional: Crypto-anchor check ---
        if body.image_base64:
            try:
                raw = base64.b64decode(body.image_base64)
                arr = np.frombuffer(raw, np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is not None and img.size > 0:
                    seed = f"{body.batch_id}:{body.serial}"
                    expected = generate_anchor(seed)
                    actual, pp_info = preprocess_photo(img, expected=expected)
                    if actual is None:
                        pp_info["reason"] = "no_qr_detected"
                        gray_fallback = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
                        actual = cv2.resize(gray_fallback, (64, 64))
                    anchor_result = compare_anchors(expected, actual)
                    anchor_result["preprocess"] = pp_info
                    metrics = anchor_result

                    # --- Optional: AI second opinion ---
                    # Runs in parallel with the hand-tuned CV. If a trained
                    # model is present (classifier.onnx), include its
                    # confidence. The hand-tuned CV is the authoritative
                    # signal; the CNN is additive.
                    ai_conf = None
                    if ml_available():
                        try:
                            proba = predict_proba(actual)
                            if proba is not None:
                                cv_says_fake = anchor_result["degraded"]
                                ai_says_fake = proba["p_counterfeit"] > 0.5
                                ai_conf = AIConfidence(
                                    p_genuine=round(proba["p_genuine"], 4),
                                    p_counterfeit=round(proba["p_counterfeit"], 4),
                                    model=proba.get("model", "cnn"),
                                    model_agrees_with_cv=(cv_says_fake == ai_says_fake),
                                )
                                # If the CNN strongly disagrees with the CV in the
                                # "more counterfeit" direction, escalate to counterfeit
                                if not cv_says_fake and ai_says_fake and proba["p_counterfeit"] > 0.85:
                                    alerts.append("counterfeit")
                                    if overlay_b64 is None:
                                        heatmap = compute_overlay(actual, expected)
                                        _, buf = cv2.imencode(".png", heatmap)
                                        overlay_b64 = base64.b64encode(buf.tobytes()).decode()
                        except Exception:
                            pass

                    if anchor_result["degraded"]:
                        heatmap = compute_overlay(actual, expected)
                        _, buf = cv2.imencode(".png", heatmap)
                        overlay_b64 = base64.b64encode(buf.tobytes()).decode()
                        alerts.append("counterfeit")
            except Exception:
                pass

        # --- Batch info ---
        batch_info = None
        batch_row = await get_batch(body.batch_id)
        if batch_row:
            route_rows = await get_route(body.batch_id)
            route = [RoutePoint(location_name=r["location_name"], lat=r["lat"], lng=r["lng"], event=r["event"]) for r in route_rows]
            batch_info = BatchInfo(
                batch_id=batch_row["batch_id"],
                region=batch_row["region"],
                mint_date=batch_row["mint_date"],
                manufacturer=batch_row.get("manufacturer", ""),
                drug_name=batch_row.get("drug_name", ""),
                drug_use=batch_row.get("drug_use", ""),
                expiry=batch_row.get("expiry", ""),
                route=route,
            )

        # --- Scan history ---
        history = await get_scan_history(body.serial)
        scan_count = await get_scan_count(body.serial)
        velocity_alert = None
        density_alert = None
        gps_alert = None
        previous_scan = None

        # Velocity check
        if scan_count > 0:
            latest = history[0]
            previous_scan = PreviousScan(lat=latest["lat"], lng=latest["lng"], timestamp=latest["timestamp"], result=latest["result"])
            velocity_alert = build_velocity_alert(latest, body.lat, body.lng, ts)
            if velocity_alert:
                alerts.append("velocity")

        # Density check
        if scan_count + 1 > DENSITY_THRESHOLD:
            density_alert = f"This serial has been scanned {scan_count + 1} times. Possible code replay."
            alerts.append("density")

        # GPS check
        if batch_info and batch_info.region:
            if not gps_in_region(body.lat, body.lng, batch_info.region):
                gps_alert = f"This batch is assigned to {batch_info.region} but scanned at ({body.lat:.1f}, {body.lng:.1f}). Possible diversion."
                alerts.append("gps")

        scan_history = ScanHistory(
            scan_count=scan_count + 1,
            velocity_alert=velocity_alert,
            density_alert=density_alert,
            gps_alert=gps_alert,
            previous_scan=previous_scan,
        )

        # --- Determine status ---
        if "counterfeit" in alerts:
            status = "counterfeit"
            message = "Crypto-anchor verification failed. Print quality deviation detected."
            confidence = anchor_result["confidence"] if anchor_result else 0.0
        elif alerts:
            status = "flagged"
            if "gps" in alerts:
                message = gps_alert or "Geographic anomaly detected."
                confidence = 0.3
            elif "velocity" in alerts:
                message = velocity_alert or "Movement anomaly detected."
                confidence = 0.3
            elif "density" in alerts:
                message = density_alert or "Scan frequency anomaly detected."
                confidence = 0.5
            else:
                message = "Anomaly detected."
                confidence = 0.3
        else:
            status = "verified"
            message = "No anomalies detected. Product is authentic."
            confidence = 1.0

        await record_scan(serial=body.serial, batch_id=body.batch_id, lat=body.lat, lng=body.lng, timestamp=ts, result=status)

        chain = await verify_chain(body.serial)
        scan_history.chain_intact = chain.get("intact")
        scan_history.chain_message = chain.get("message")

        return VerifyResponse(
            status=status,
            confidence=confidence,
            message=message,
            metrics=metrics if metrics else ({"note": "No crypto-anchor image provided"} if not body.image_base64 else None),
            overlay_base64=overlay_b64,
            batch_info=batch_info,
            scan_history=scan_history,
            ai_confidence=ai_conf,
        )

    except Exception as e:
        return VerifyResponse(
            status="error", confidence=0.0, message=f"Verification failed: {str(e)}"
        )


@app.get("/api/v1/chain/verify")
async def chain_verify(serial: str = ""):
    if not serial:
        return {"intact": True, "message": "No serial provided"}
    result = await verify_chain(serial)
    return result


@app.post("/api/v1/register", response_model=RegisterBatchResponse)
async def register_batch(body: RegisterBatchRequest):
    """Register a new batch with its supply chain route.

    Used by manufacturer/distributor partners to onboard their batches
    into the AntiFake system. Idempotent: re-registering an existing
    batch updates the metadata and route.
    """
    if not body.batch_id or not body.region or not body.mint_date:
        return RegisterBatchResponse(
            batch_id=body.batch_id,
            inserted=False,
            message="batch_id, region, and mint_date are required",
        )
    inserted = await upsert_batch(
        batch_id=body.batch_id,
        region=body.region,
        mint_date=body.mint_date,
        manufacturer=body.manufacturer,
        drug_name=body.drug_name,
        drug_use=body.drug_use,
        expiry=body.expiry,
    )
    # Replace the route if any new points are provided
    if body.route:
        await clear_route(body.batch_id)
        for i, p in enumerate(body.route, start=1):
            await add_route_point(
                batch_id=body.batch_id,
                point_order=i,
                location_name=p.location_name,
                lat=p.lat,
                lng=p.lng,
                event=p.event,
            )
    msg = "Batch registered" if inserted else "Batch updated"
    return RegisterBatchResponse(batch_id=body.batch_id, inserted=inserted, message=msg)


@app.get("/api/v1/batches", response_model=ListBatchesResponse)
async def list_all_batches():
    """List all registered batches (for partner dashboards)."""
    rows = await list_batches()
    items: list[BatchInfo] = []
    for r in rows:
        route_rows = await get_route(r["batch_id"])
        route = [
            RoutePoint(location_name=p["location_name"], lat=p["lat"], lng=p["lng"], event=p["event"])
            for p in route_rows
        ]
        items.append(
            BatchInfo(
                batch_id=r["batch_id"],
                region=r["region"],
                mint_date=r["mint_date"],
                manufacturer=r.get("manufacturer", ""),
                drug_name=r.get("drug_name", ""),
                drug_use=r.get("drug_use", ""),
                expiry=r.get("expiry", ""),
                route=route,
            )
        )
    return ListBatchesResponse(batches=items, total=len(items))


web_dir = os.path.join(os.path.dirname(__file__), "..", "..", "web")
if os.path.isdir(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
