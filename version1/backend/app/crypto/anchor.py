import base64

import cv2
import numpy as np

DEGRADATION_THRESHOLD = 0.3


def _decode_image(data: str) -> np.ndarray:
    raw = base64.b64decode(data)
    arr = np.frombuffer(raw, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("invalid image data")
    return img


async def verify_anchor(image_b64: str) -> dict:
    try:
        img = _decode_image(image_b64)
    except (ValueError, Exception):
        return {"degraded": True, "reason": "unreadable"}

    edges = cv2.Canny(img, 50, 150)
    total_pixels = img.size
    edge_pixels = int(np.sum(edges > 0))
    bleed_ratio = edge_pixels / total_pixels

    degraded = bleed_ratio > DEGRADATION_THRESHOLD
    return {
        "degraded": degraded,
        "bleed_ratio": round(float(bleed_ratio), 4),
    }
