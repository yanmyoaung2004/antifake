"""
Photo preprocessing pipeline (simple, geometric).

For real phone photos, the CV module works best when the photo is
approximately axis-aligned and well-lit. This pipeline:
  1. Detects the QR code with cv2.QRCodeDetector
  2. Computes a similarity transform from the template to the photo
  3. Crops the 64x64 anchor region at the predicted location
  4. Optionally refines the position with a small NCC search

For real-world phone photos with rotation, perspective, blur, and
lighting variations, the CV module is a "best effort" signal that
complements the spatial-temporal + hash chain (which are authoritative).

If no QR is detected, the CV is skipped entirely and the verification
falls back to the spatial-temporal + chain checks (which work with just
batch/serial numbers, no image).
"""
from __future__ import annotations

import cv2
import numpy as np

ANCHOR_SIZE = 64

# Template layout matches tools/printable_labels.py LABEL_SIZE = (600, 400)
# The QR is at (330, 80) sized 240x240. cv2.QRCodeDetector returns the
# outer module corners, measured empirically at (340, 90) - (559, 309).
TEMPLATE_W = 600
TEMPLATE_H = 400
QR_X, QR_Y, QR_S = 330, 80, 240

# Anchor region in the template, in template pixel coordinates.
ANCHOR_X, ANCHOR_Y, ANCHOR_W, ANCHOR_H = 30, 80, 64, 64

# Number of modules in the printed QR (Version 2 = 25 modules).
QR_MODULES = 25
QR_MODULE_PX = QR_S / QR_MODULES  # 9.6 px

# Sub-pixel offset from the detector's QR-TL to the noise's TL.
# detector_TL is at printed_TL + 1 module = (330 + 9.6, 80 + 9.6) = (339.6, 89.6)
# noise_TL is at (30, 80)
# offset = noise_TL - detector_TL
_ANCHOR_OFFSET_FROM_DETECTOR_X = (ANCHOR_X) - (QR_X + QR_MODULE_PX)
_ANCHOR_OFFSET_FROM_DETECTOR_Y = (ANCHOR_Y) - (QR_Y + QR_MODULE_PX)


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Order 4 corner points as: top-left, top-right, bottom-right, bottom-left."""
    pts = pts.reshape(4, 2).astype(np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()
    out = np.zeros((4, 2), dtype=np.float32)
    out[0] = pts[np.argmin(s)]
    out[2] = pts[np.argmax(s)]
    out[1] = pts[np.argmin(diff)]
    out[3] = pts[np.argmax(diff)]
    return out


def detect_qr_corners(gray: np.ndarray) -> np.ndarray | None:
    """Return 4x2 array of QR corners in image coordinates, or None."""
    detector = cv2.QRCodeDetector()
    decoded, points, _ = detector.detectAndDecode(gray)
    if points is None or len(points) != 4:
        try:
            multi_detector = cv2.QRCodeDetectorAruco()
            _, decoded, points, _ = multi_detector.detectAndDecodeMulti(gray)
        except Exception:
            points = None
        if points is None or len(points) == 0:
            return None
    return _order_corners(points[0])


def _qr_corners_in_template() -> np.ndarray:
    """Detector-equivalent QR corners in template coordinates (measured)."""
    return np.array(
        [[340.0, 90.0], [559.0, 90.0], [559.0, 309.0], [340.0, 309.0]],
        dtype=np.float32,
    )


def _anchor_corners_in_template() -> np.ndarray:
    return np.array(
        [
            [ANCHOR_X, ANCHOR_Y],
            [ANCHOR_X + ANCHOR_W, ANCHOR_Y],
            [ANCHOR_X + ANCHOR_W, ANCHOR_Y + ANCHOR_H],
            [ANCHOR_X, ANCHOR_Y + ANCHOR_H],
        ],
        dtype=np.float32,
    )


def extract_anchor_from_photo(
    image_bgr: np.ndarray,
    qr_corners: np.ndarray,
    expected: np.ndarray | None = None,
) -> np.ndarray | None:
    """
    Given a photo and its detected QR corners (in TL, TR, BR, BL order),
    return a canonical 64x64 grayscale crop of the anchor region.
    """
    if image_bgr is None or image_bgr.size == 0:
        return None
    gray = image_bgr if image_bgr.ndim == 2 else cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    qr_tl = qr_corners[0]
    qr_tr = qr_corners[1]
    qr_width_photo = float(np.linalg.norm(qr_tr - qr_tl))
    detector_effective_width = (QR_MODULES - 2) * QR_MODULE_PX
    scale = qr_width_photo / detector_effective_width

    anchor_tl_x = qr_tl[0] + _ANCHOR_OFFSET_FROM_DETECTOR_X * scale
    anchor_tl_y = qr_tl[1] + _ANCHOR_OFFSET_FROM_DETECTOR_Y * scale
    crop_size = max(16, int(round(ANCHOR_SIZE * scale)))
    H_img, W_img = gray.shape

    def _crop_at_int(x: int, y: int, size: int) -> np.ndarray | None:
        if x < 0 or y < 0 or x + size > W_img or y + size > H_img:
            return None
        return gray[y:y + size, x:x + size]

    # Compute the predicted crop position
    x0_pred = int(round(anchor_tl_x))
    y0_pred = int(round(anchor_tl_y))

    if expected is not None and crop_size >= 32:
        # Use a fixed 64x64 template (the expected noise at its native size).
        # Search a 9x9 window around the predicted position to correct
        # 1-2 pixel QR detection jitter and ~1% scale error.
        size = 64
        e = expected.astype(np.float32)
        e_n = (e - e.mean()) / (e.std() + 1e-6)
        cx0 = x0_pred
        cy0 = y0_pred
        best = (0, 0, -1.0)
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                x0 = cx0 + dx
                y0 = cy0 + dy
                patch = _crop_at_int(x0, y0, size)
                if patch is None:
                    continue
                p = patch.astype(np.float32)
                p = (p - p.mean()) / (p.std() + 1e-6)
                ncc = float((e_n * p).mean())
                if ncc > best[2]:
                    best = (dx, dy, ncc)
        dx, dy, _ = best
        cropped = _crop_at_int(cx0 + dx, cy0 + dy, size)
        if cropped is not None:
            return cropped

    cropped = _crop_at_int(x0_pred, y0_pred, crop_size)
    if cropped is None:
        return None
    return cv2.resize(cropped, (ANCHOR_SIZE, ANCHOR_SIZE), interpolation=cv2.INTER_AREA)


def preprocess_photo(
    image_bgr: np.ndarray,
    expected: np.ndarray | None = None,
) -> tuple[np.ndarray | None, dict]:
    """
    Full pipeline: photo (BGR or grayscale) -> canonical 64x64 anchor.

    Returns (anchor_64x64, info_dict). anchor is None if no QR was found.
    """
    info: dict = {"qr_found": False, "qr_corners": None}
    if image_bgr is None or image_bgr.size == 0:
        return None, info
    gray = image_bgr if image_bgr.ndim == 2 else cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    corners = detect_qr_corners(gray)
    if corners is None:
        return None, info
    info["qr_found"] = True
    info["qr_corners"] = corners.tolist()
    color_input = image_bgr if image_bgr.ndim == 3 else cv2.cvtColor(image_bgr, cv2.COLOR_GRAY2BGR)
    anchor = extract_anchor_from_photo(color_input, corners, expected=expected)
    if anchor is None:
        return None, info
    return anchor, info


def synthesize_phone_photo(
    label_rgb: np.ndarray,
    blur_sigma: float = 0.8,
    rotation_deg: float = 0.0,
    perspective_strength: float = 0.0,
    brightness: float = 1.0,
    noise: float = 0.0,
    pad: int = 60,
) -> np.ndarray:
    """Simulate a real phone photo of a printed label."""
    h, w = label_rgb.shape[:2]
    bgr = cv2.cvtColor(label_rgb, cv2.COLOR_RGB2BGR)

    if perspective_strength > 0:
        rng = np.random.default_rng(int(perspective_strength * 1000))
        margin = int(min(h, w) * perspective_strength)
        src = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
        dst = src.copy()
        dst += rng.integers(-margin, margin + 1, dst.shape).astype(np.float32)
        M = cv2.getPerspectiveTransform(src, dst)
        bgr = cv2.warpPerspective(bgr, M, (w, h), borderValue=(40, 40, 40))

    if rotation_deg != 0:
        c = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(c, rotation_deg, 1.0)
        bgr = cv2.warpAffine(bgr, M, (w, h), borderValue=(40, 40, 40))

    canvas = np.full((h + 2 * pad, w + 2 * pad, 3), 40, dtype=np.uint8)
    canvas[pad : pad + h, pad : pad + w] = bgr

    if brightness != 1.0:
        canvas = np.clip(canvas.astype(np.float32) * brightness, 0, 255).astype(np.uint8)

    if blur_sigma > 0:
        canvas = cv2.GaussianBlur(canvas, (0, 0), blur_sigma)

    if noise > 0:
        rng = np.random.default_rng(int(noise * 1000))
        n = rng.integers(0, int(64 * noise), canvas.shape, dtype=np.uint8)
        canvas = cv2.add(canvas, n)

    return canvas
