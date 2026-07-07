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
from app.main import app

GENUINE_COUNT = 50
COUNTERFEIT_COUNT = 50


def _anchor_to_b64(anchor: np.ndarray) -> str:
    _, buf = cv2.imencode(".png", anchor)
    return base64.b64encode(buf.tobytes()).decode()


async def run_benchmark():
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
    accuracy = (results["tp"] + results["tn"]) / total * 100
    precision = results["tp"] / (results["tp"] + results["fp"]) * 100 if (results["tp"] + results["fp"]) > 0 else 0
    recall = results["tp"] / (results["tp"] + results["fn"]) * 100 if (results["tp"] + results["fn"]) > 0 else 0

    print(f"\n{'='*50}")
    print(f"  Accuracy Benchmark Results")
    print(f"{'='*50}")
    print(f"  Total samples:    {total}")
    print(f"  Genuine:          {GENUINE_COUNT}")
    print(f"  Counterfeit:      {COUNTERFEIT_COUNT}")
    print(f"  True positives:   {results['tp']}")
    print(f"  True negatives:   {results['tn']}")
    print(f"  False positives:  {results['fp']}")
    print(f"  False negatives:  {results['fn']}")
    print(f"  Accuracy:         {accuracy:.1f}%")
    print(f"  Precision:        {precision:.1f}%")
    print(f"  Recall:           {recall:.1f}%")
    print(f"{'='*50}")

    return results


if __name__ == "__main__":
    asyncio.run(run_benchmark())
