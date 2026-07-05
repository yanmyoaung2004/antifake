"""
Generates printable label images for physical demo boxes.

Output: demo_labels/ directory with PNG files ready to print on sticker paper.

Each label contains:
  - Layer 1: Standard QR code encoding "batch_id|serial"
  - Layer 2: Crypto-anchor noise pattern
  - Text: batch ID, serial, and "GENUINE" or "COUNTERFEIT" marker
"""

import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import qrcode
from PIL import Image, ImageDraw, ImageFont

from app.crypto.anchor import generate_anchor, simulate_photocopy

LABEL_SIZE = (600, 400)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 38, 38)
GREEN = (22, 163, 74)


def make_label(
    batch_id: str, serial: str, counterfeit: bool = False, severity: float = 0.35
) -> Image:
    label = Image.new("RGB", LABEL_SIZE, WHITE)
    draw = ImageDraw.Draw(label)

    seed = f"{batch_id}:{serial}"
    anchor = generate_anchor(seed)
    if counterfeit:
        anchor = simulate_photocopy(anchor, severity)

    anchor_img = Image.fromarray(anchor, mode="L")
    label.paste(anchor_img, (30, 80))

    qr = qrcode.QRCode(border=1)
    qr.add_data(f"{batch_id}|{serial}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_resized = qr_img.resize((240, 240))
    label.paste(qr_resized, (330, 80))

    draw.text((30, 20), f"Batch: {batch_id}   Serial: {serial}", fill=BLACK)
    draw.text((30, 360), "LAYER 1 — QR Code", fill=(100, 100, 100))
    draw.text((330, 360), "LAYER 2 — Crypto Anchor", fill=(100, 100, 100))

    status = "COUNTERFEIT" if counterfeit else "GENUINE"
    color = RED if counterfeit else GREEN
    for offset in range(4, 0, -1):
        draw.text(
            (LABEL_SIZE[0] // 2 - 60, LABEL_SIZE[1] - 40),
            status,
            fill=(255, 255, 255) if offset == 0 else color,
        )
    draw.text(
        (LABEL_SIZE[0] // 2 - 58, LABEL_SIZE[1] - 42),
        status,
        fill=color,
    )

    return label


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "demo_labels")
    os.makedirs(out_dir, exist_ok=True)

    labels = [
        ("BATCH-A", "001", False),
        ("BATCH-A", "002", True),
    ]

    for batch_id, serial, counterfeit in labels:
        label = make_label(batch_id, serial, counterfeit)
        tag = "counterfeit" if counterfeit else "genuine"
        path = os.path.join(out_dir, f"label_{batch_id}_{serial}_{tag}.png")
        label.save(path)
        print(f"  Saved: {path}")

    print(f"\nDone. Print these on sticker paper and attach to demo boxes.")
    print("Place a GENUINE label on one box and a COUNTERFEIT label on another.")


if __name__ == "__main__":
    main()
