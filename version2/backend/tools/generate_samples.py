"""
Generates sample anchor images for testing and demo.

Usage: uv run python tools/generate_samples.py

Outputs to sample_images/:
  - genuine_<batch>_<serial>.png  — clean anchor from seed
  - tampered_<batch>_<serial>.png — anchor with simulated photocopy degradation
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np

from app.crypto.anchor import generate_anchor, ANCHOR_SIZE


def simulate_photocopy(anchor: np.ndarray, severity: float = 0.3) -> np.ndarray:
    blurred = cv2.GaussianBlur(anchor, (3, 3), 0.5)
    noise = np.random.default_rng(42).integers(0, int(64 * severity), anchor.shape, dtype=np.uint8)
    tampered = cv2.addWeighted(blurred, 1.0 - severity, noise, severity, 0)
    return np.clip(tampered, 0, 255).astype(np.uint8)


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "sample_images")
    os.makedirs(out_dir, exist_ok=True)

    samples = [
        ("BATCH-A", "001"),
        ("BATCH-A", "002"),
        ("BATCH-B", "001"),
    ]

    for batch_id, serial in samples:
        seed = f"{batch_id}:{serial}"
        anchor = generate_anchor(seed)

        genuine_path = os.path.join(out_dir, f"genuine_{batch_id}_{serial}.png")
        cv2.imwrite(genuine_path, anchor)
        print(f"  Generated: {genuine_path}")

        tampered = simulate_photocopy(anchor, severity=0.35)
        tampered_path = os.path.join(out_dir, f"tampered_{batch_id}_{serial}.png")
        cv2.imwrite(tampered_path, tampered)
        print(f"  Generated: {tampered_path}")

    print(f"\nDone. {len(samples) * 2} images saved to {out_dir}")


if __name__ == "__main__":
    main()
