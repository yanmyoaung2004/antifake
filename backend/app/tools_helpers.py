"""
Printable label helpers.

Shared between tools/printable_labels.py (one-off generator) and
tools/photo_robustness.py (synthesizes test photos).

Layout: 600x400 white label with:
  - QR code on the right (registration mark for the verifier app)
  - Crypto-anchor noise on the left (the thing being verified)
  - Text: batch, serial, GENUINE/COUNTERFEIT marker
"""
from __future__ import annotations

from PIL import Image, ImageDraw

import numpy as np
import qrcode

from app.crypto.anchor import generate_anchor, simulate_photocopy

LABEL_SIZE = (600, 400)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 38, 38)
GREEN = (22, 163, 74)


def make_label_rgb(
    batch_id: str,
    serial: str,
    counterfeit: bool = False,
    severity: float = 0.35,
    as_pil: bool = False,
):
    """
    Build a printable label.

    Returns numpy RGB array by default; set as_pil=True for a PIL Image.
    """
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

    if as_pil:
        return label
    return np.array(label)
