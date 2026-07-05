import base64

import cv2
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

from app.crypto.anchor import generate_anchor, extract_noise, compare_anchors, compute_overlay

app = FastAPI(title="AntiFake v2")


class VerifyRequest(BaseModel):
    batch_id: str
    serial: str
    image_base64: str


class VerifyResponse(BaseModel):
    status: str
    confidence: float
    message: str
    metrics: dict | None = None
    overlay_base64: str | None = None


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/verify", response_model=VerifyResponse)
async def verify(body: VerifyRequest):
    try:
        raw = base64.b64decode(body.image_base64)
        arr = np.frombuffer(raw, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return VerifyResponse(
                status="error", confidence=0.0, message="Could not decode image."
            )

        seed = f"{body.batch_id}:{body.serial}"
        expected = generate_anchor(seed)
        actual = extract_noise(img)

        result = compare_anchors(expected, actual)

        overlay_b64 = None
        if result["degraded"]:
            heatmap = compute_overlay(actual, expected)
            _, buf = cv2.imencode(".png", heatmap)
            overlay_b64 = base64.b64encode(buf.tobytes()).decode()

        if result["degraded"]:
            return VerifyResponse(
                status="counterfeit",
                confidence=result["confidence"],
                message="Print quality deviation detected. Likely counterfeit.",
                metrics=result,
                overlay_base64=overlay_b64,
            )

        return VerifyResponse(
            status="verified",
            confidence=result["confidence"],
            message="Anchor pattern matches. Authentic.",
            metrics=result,
        )

    except Exception as e:
        return VerifyResponse(
            status="error", confidence=0.0, message=f"Verification failed: {str(e)}"
        )
