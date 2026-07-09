"""
Accuracy benchmark: tests 100 samples (50 genuine, 50 counterfeit)
through the verify endpoint and reports detection metrics.

Usage: uv run python tools/benchmark.py
"""

import base64
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np
from httpx import ASGITransport, AsyncClient
import asyncio

from app.crypto.anchor import generate_anchor, simulate_photocopy
from app.database import init_db
from app.main import app

GENUINE_COUNT = 50
COUNTERFEIT_COUNT = 50


def _anchor_to_b64(anchor: np.ndarray) -> str:
    _, buf = cv2.imencode(".png", anchor)
    return base64.b64encode(buf.tobytes()).decode()


async def run_benchmark():
    await init_db()
    transport = ASGITransport(app=app)
    results = {"tp": 0, "tn": 0, "fp": 0, "fn": 0, "times": []}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Genuine samples — should all return "verified"
        for i in range(GENUINE_COUNT):
            seed = f"BENCH:GENUINE-{i}"
            anchor = generate_anchor(seed)
            b64 = _anchor_to_b64(anchor)
            resp = await client.post("/api/v1/verify", json={
                "batch_id": "BENCH", "serial": f"GENUINE-{i}",
                "image_base64": b64, "lat": 0, "lng": 0, "timestamp": "2026-07-07T00:00:00",
            })
            d = resp.json()
            if d["status"] == "verified":
                results["tp"] += 1
            else:
                results["fn"] += 1
                print(f"  FALSE NEGATIVE: genuine sample {i} flagged as {d['status']}")

        # Counterfeit samples — should all return "counterfeit"
        for i in range(COUNTERFEIT_COUNT):
            seed = f"BENCH:FAKE-{i}"
            anchor = generate_anchor(seed)
            tampered = simulate_photocopy(anchor, severity=0.35)
            b64 = _anchor_to_b64(tampered)
            resp = await client.post("/api/v1/verify", json={
                "batch_id": "BENCH", "serial": f"FAKE-{i}",
                "image_base64": b64, "lat": 0, "lng": 0, "timestamp": "2026-07-07T00:00:00",
            })
            d = resp.json()
            if d["status"] == "counterfeit":
                results["tn"] += 1
            else:
                results["fp"] += 1
                print(f"  FALSE POSITIVE: counterfeit sample {i} flagged as {d['status']}")

    total = GENUINE_COUNT + COUNTERFEIT_COUNT
    cv_accuracy = (results["tp"] + results["tn"]) / total * 100
    cv_precision = results["tp"] / (results["tp"] + results["fp"]) * 100 if (results["tp"] + results["fp"]) > 0 else 0
    cv_recall = results["tp"] / (results["tp"] + results["fn"]) * 100 if (results["tp"] + results["fn"]) > 0 else 0

    print(f"\n{'='*50}")
    print(f"  Accuracy Benchmark Results")
    print(f"{'='*50}")
    print(f"  Total samples:    {total}")
    print(f"  Genuine:          {GENUINE_COUNT}")
    print(f"  Counterfeit:      {COUNTERFEIT_COUNT}")
    print(f"\n  Hand-tuned CV:")
    print(f"    True positives:   {results['tp']}")
    print(f"    True negatives:   {results['tn']}")
    print(f"    False positives:  {results['fp']}")
    print(f"    False negatives:  {results['fn']}")
    print(f"    Accuracy:         {cv_accuracy:.1f}%")
    print(f"    Precision:        {cv_precision:.1f}%")
    print(f"    Recall:           {cv_recall:.1f}%")

    # Check if CNN is available (model was loaded during verify requests)
    # Re-run and collect ai_confidence for CNN comparison
    cnn_results = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    cnn_used = False
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i in range(GENUINE_COUNT):
            seed = f"BENCH-CNN:G-{i}"
            anchor = generate_anchor(seed)
            b64 = _anchor_to_b64(anchor)
            resp = await client.post("/api/v1/verify", json={
                "batch_id": "BENCH", "serial": f"CNN-G{i}",
                "image_base64": b64, "lat": 0, "lng": 0, "timestamp": "2026-07-07T00:00:00",
            })
            d = resp.json()
            ai = d.get("ai_confidence")
            if ai and ai.get("p_counterfeit") is not None:
                cnn_used = True
                is_fake_pred = ai["p_counterfeit"] > 0.5
                if not is_fake_pred:
                    cnn_results["tp"] += 1
                else:
                    cnn_results["fn"] += 1

        for i in range(COUNTERFEIT_COUNT):
            seed = f"BENCH-CNN:F-{i}"
            anchor = generate_anchor(seed)
            tampered = simulate_photocopy(anchor, severity=0.35)
            b64 = _anchor_to_b64(tampered)
            resp = await client.post("/api/v1/verify", json={
                "batch_id": "BENCH", "serial": f"CNN-F{i}",
                "image_base64": b64, "lat": 0, "lng": 0, "timestamp": "2026-07-07T00:00:00",
            })
            d = resp.json()
            ai = d.get("ai_confidence")
            if ai and ai.get("p_counterfeit") is not None:
                cnn_used = True
                is_fake_pred = ai["p_counterfeit"] > 0.5
                if is_fake_pred:
                    cnn_results["tn"] += 1
                else:
                    cnn_results["fp"] += 1

    if cnn_used:
        cnn_tp = cnn_results["tp"]
        cnn_tn = cnn_results["tn"]
        cnn_fp = cnn_results["fp"]
        cnn_fn = cnn_results["fn"]
        cnn_total = cnn_tp + cnn_tn + cnn_fp + cnn_fn
        cnn_accuracy = (cnn_tp + cnn_tn) / cnn_total * 100 if cnn_total > 0 else 0
        cnn_precision = cnn_tp / (cnn_tp + cnn_fp) * 100 if (cnn_tp + cnn_fp) > 0 else 0
        cnn_recall = cnn_tp / (cnn_tp + cnn_fn) * 100 if (cnn_tp + cnn_fn) > 0 else 0

        print(f"\n  CNN classifier:")
        print(f"    True positives:   {cnn_tp}")
        print(f"    True negatives:   {cnn_tn}")
        print(f"    False positives:  {cnn_fp}")
        print(f"    False negatives:  {cnn_fn}")
        print(f"    Accuracy:         {cnn_accuracy:.1f}%")
        print(f"    Precision:        {cnn_precision:.1f}%")
        print(f"    Recall:           {cnn_recall:.1f}%")
    else:
        print(f"\n  CNN classifier:  NOT AVAILABLE (no classifier.onnx found)")

    print(f"{'='*50}")

    return results


if __name__ == "__main__":
    if os.path.exists("antifake.db"):
        os.remove("antifake.db")
    asyncio.run(run_benchmark())
