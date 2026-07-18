"""
Photo preprocessing pipeline.

For real phone photos, the CV module is a "best effort" signal that
complements the spatial-temporal + hash chain (which are authoritative).

Pipeline:
  1. Detect QR code corners with cv2.QRCodeDetector
  2. Fit a similarity transform (rotation + uniform scale + translation)
     from the template's QR detector corners to the photo's corners.
     This is 4-DOF, not the full 8-DOF homography — avoids perspective
     interpolation blur that destroys the noise pattern.
  3. Project the anchor's template position into photo coordinates
     using the similarity transform.
  4. Coarse-to-fine NCC search:
     - Coarse: 21x21 window at step 2 pixels around the predicted center
     - Fine: 5x5 window at step 1 pixel around the coarse best
     This corrects the 1-3px QR detection jitter.

If no QR is detected, returns None and the system falls back to
spatial-temporal + hash chain checks (no image needed).
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
    return a canonical 64×64 grayscale crop of the anchor region.

    Strategy:
      1. Homography from template QR corners to photo QR corners
         (8-DOF, handles perspective correctly).
      2. Project the 4 anchor corners from template → photo.
      3. Compute a slightly padded axis-aligned bounding box.
      4. Crop the bbox from the photo (no warp, no interpolation blur).
      5. Coarse-to-fine NCC search within the crop to find the exact
         64×64 region.
    """
    if image_bgr is None or image_bgr.size == 0:
        return None
    gray = image_bgr if image_bgr.ndim == 2 else cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    H_img, W_img = gray.shape

    template_qr = _qr_corners_in_template()
    H, _ = cv2.findHomography(template_qr, qr_corners, method=0)
    if H is None:
        return None

    # Project anchor corners template → photo
    anchor_template = np.array(
        [
            [ANCHOR_X, ANCHOR_Y],
            [ANCHOR_X + ANCHOR_W, ANCHOR_Y],
            [ANCHOR_X + ANCHOR_W, ANCHOR_Y + ANCHOR_H],
            [ANCHOR_X, ANCHOR_Y + ANCHOR_H],
        ],
        dtype=np.float32,
    )
    anchor_photo = cv2.perspectiveTransform(
        anchor_template.reshape(1, 4, 2).astype(np.float32), H
    ).reshape(4, 2)
    if not np.all(np.isfinite(anchor_photo)):
        return None

    # Bounding box with generous padding for the NCC search to work with
    x_min = max(0, int(round(anchor_photo[:, 0].min())) - 24)
    y_min = max(0, int(round(anchor_photo[:, 1].min())) - 24)
    x_max = min(W_img, int(round(anchor_photo[:, 0].max())) + 24)
    y_max = min(H_img, int(round(anchor_photo[:, 1].max())) + 24)
    if x_max - x_min < ANCHOR_SIZE or y_max - y_min < ANCHOR_SIZE:
        return None
    crop_region = gray[y_min:y_max, x_min:x_max]

    if expected is not None and crop_region.size >= 64 * 64 * 2:
        # NCC search within the padded crop region
        search_h, search_w = crop_region.shape
        max_dx = search_w - ANCHOR_SIZE
        max_dy = search_h - ANCHOR_SIZE
        if max_dx < 0 or max_dy < 0:
            return crop_region[:ANCHOR_SIZE, :ANCHOR_SIZE]
        e = expected.astype(np.float32)
        e_n = (e - e.mean()) / (e.std() + 1e-6)
        best = (0, 0, -1.0)
        # Coarse: search at step 2
        for dy in range(0, max_dy + 1, 2):
            for dx in range(0, max_dx + 1, 2):
                patch = crop_region[dy:dy + ANCHOR_SIZE, dx:dx + ANCHOR_SIZE]
                p = patch.astype(np.float32)
                p = (p - p.mean()) / (p.std() + 1e-6)
                ncc = float((e_n * p).mean())
                if ncc > best[2]:
                    best = (dx, dy, ncc)
        # Fine: step 1 around the best
        sd = range(-1, 2)
        for dy in sd:
            for dx in sd:
                cx = best[0] + dx
                cy = best[1] + dy
                if cx < 0 or cy < 0 or cx + ANCHOR_SIZE > search_w or cy + ANCHOR_SIZE > search_h:
                    continue
                patch = crop_region[cy:cy + ANCHOR_SIZE, cx:cx + ANCHOR_SIZE]
                p = patch.astype(np.float32)
                p = (p - p.mean()) / (p.std() + 1e-6)
                ncc = float((e_n * p).mean())
                if ncc > best[2]:
                    best = (cx, cy, ncc)
        dx, dy, _ = best
        return crop_region[dy:dy + ANCHOR_SIZE, dx:dx + ANCHOR_SIZE]

    # Fallback: center crop of the bbox
    cx = (x_min + x_max) // 2
    cy = (y_min + y_max) // 2
    x0 = cx - ANCHOR_SIZE // 2
    y0 = cy - ANCHOR_SIZE // 2
    if x0 < 0 or y0 < 0 or x0 + ANCHOR_SIZE > W_img or y0 + ANCHOR_SIZE > H_img:
        return None
    return gray[y0:y0 + ANCHOR_SIZE, x0:x0 + ANCHOR_SIZE]


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
