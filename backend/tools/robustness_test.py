"""
Real-world robustness and adversarial testing.

Tests crypto-anchor verification against:
  - Phone camera blur (Gaussian)
  - Low-light noise
  - Resize (different camera resolutions)
  - Rotation (angled photos)
  - Various photocopy severity levels

Usage: python tools/robustness_test.py
"""

import os, sys, base64, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2, numpy as np
from httpx import ASGITransport, AsyncClient
from app.crypto.anchor import generate_anchor
from app.database import init_db
from app.main import app

from app.main import app


def apply_blur(img, sigma):
    return cv2.GaussianBlur(img, (5, 5), sigma)


def apply_noise(img, severity):
    noise = np.random.default_rng(42).integers(0, int(64 * severity), img.shape, dtype=np.uint8)
    return np.clip(img.astype(int) + noise - int(64 * severity / 2), 0, 255).astype(np.uint8)


def apply_resize(img, factor):
    h = int(img.shape[0] * factor)
    w = int(img.shape[1] * factor)
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_LINEAR)


def apply_rotate(img, degrees):
    c = (img.shape[1] // 2, img.shape[0] // 2)
    m = cv2.getRotationMatrix2D(c, degrees, 1.0)
    return cv2.warpAffine(img, m, (img.shape[1], img.shape[0]), borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def anchor_to_b64(img):
    if img.shape[-2:] != (64, 64):
        img = cv2.resize(img, (64, 64), interpolation=cv2.INTER_AREA)
    _, buf = cv2.imencode(".png", img)
    return base64.b64encode(buf.tobytes()).decode()


async def run_test():
    transport = ASGITransport(app=app)
    await init_db()

    scenarios = {
        "Perfect match":                 lambda a: a,
        "Camera blur (mild)":             lambda a: apply_blur(a, 1.0),
        "Camera blur (moderate)":         lambda a: apply_blur(a, 2.0),
        "Camera blur (heavy)":            lambda a: apply_blur(a, 4.0),
        "Low light noise (mild)":         lambda a: apply_noise(a, 0.1),
        "Low light noise (heavy)":        lambda a: apply_noise(a, 0.3),
        "Resize 50% (low-res camera)":    lambda a: apply_resize(a, 0.5),
        "Resize 150% (upscaled)":         lambda a: apply_resize(a, 1.5),
        "Rotation 5deg (angled)":         lambda a: apply_rotate(a, 5),
        "Rotation 15deg (angled)":        lambda a: apply_rotate(a, 15),
        "Photocopy (mild degradation)":   lambda a: apply_noise(a, 0.15),
        "Photocopy (moderate)":           lambda a: apply_noise(a, 0.25),
        "Photocopy (heavy degradation)":  lambda a: apply_noise(a, 0.4),
        "High-end printer copy":          lambda a: apply_blur(a, 0.5),
    }

    print(f"\n{'='*60}")
    print(f"  Robustness & Adversarial Test")
    print(f"{'='*60}")
    genuine_total = 0
    flagged_total = 0

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i, (label, transform) in enumerate(scenarios.items()):
            ser = f"R{i:03d}"
            anchor = generate_anchor(f"ROBUST:{ser}")
            img = transform(anchor)
            b64 = anchor_to_b64(img)
            resp = await client.post("/api/v1/verify", json={
                "batch_id": "ROBUST", "serial": ser, "image_base64": b64,
                "lat": 21.0, "lng": 96.0, "timestamp": "2026-07-07T10:00:00",
            })
            d = resp.json()
            status = d["status"]
            conf = (d.get("metrics") or {}).get("confidence", 0)
            is_genuine = status == "verified"

            if is_genuine:
                genuine_total += 1
            else:
                flagged_total += 1

            indicator = "PASS" if is_genuine else "FLAG"
            print(f"  {indicator} {label:40s} -> {status:12s} conf:{conf:.0%}")

        print(f"{'='*60}")
        print(f"  Genuine (passed):   {genuine_total}/{len(scenarios)}  ({genuine_total/len(scenarios)*100:.0f}%)")
        print(f"  Flagged (caught):   {flagged_total}/{len(scenarios)}  ({flagged_total/len(scenarios)*100:.0f}%)")
        print(f"  Note: Blur/noise/angle of genuine should pass.")
        print(f"        Heavy damage & photocopy should flag.")
        print(f"{'='*60}")


if __name__ == "__main__":
    if os.path.exists("antifake.db"):
        os.remove("antifake.db")
    asyncio.run(run_test())
