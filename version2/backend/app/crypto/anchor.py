import hashlib

import cv2
import numpy as np

ANCHOR_SIZE = 64
BLEED_THRESHOLD = 0.25
HIST_CORR_THRESHOLD = 0.6


def generate_anchor(seed: str) -> np.ndarray:
    digest = hashlib.sha256(seed.encode()).digest()
    rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
    return rng.integers(0, 256, (ANCHOR_SIZE, ANCHOR_SIZE), dtype=np.uint8)


def extract_noise(image_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    size = ANCHOR_SIZE
    h, w = gray.shape
    if h < size or w < size:
        gray = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA)
    return gray[:size, :size]


def compute_overlay(actual: np.ndarray, expected: np.ndarray) -> np.ndarray:
    diff = cv2.absdiff(expected, actual)
    diff_norm = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
    heatmap = cv2.applyColorMap(diff_norm, cv2.COLORMAP_JET)
    return heatmap


def compare_anchors(expected: np.ndarray, actual: np.ndarray) -> dict:
    if expected.shape != actual.shape:
        actual = cv2.resize(actual, (expected.shape[1], expected.shape[0]))

    grad_expected = np.gradient(expected.astype(float))
    grad_actual = np.gradient(actual.astype(float))
    edge_sharpness = float(np.mean(np.abs(grad_actual)) / max(np.mean(np.abs(grad_expected)), 1e-6))

    edges_expected = cv2.Canny(expected, 50, 150)
    edges_actual = cv2.Canny(actual, 50, 150)
    edge_diff_ratio = float(np.sum(edges_actual > 0) / max(np.sum(edges_expected > 0), 1))

    hist_expected = cv2.calcHist([expected], [0], None, [32], [0, 256])
    hist_actual = cv2.calcHist([actual], [0], None, [32], [0, 256])
    cv2.normalize(hist_expected, hist_expected)
    cv2.normalize(hist_actual, hist_actual)
    hist_corr = float(cv2.compareHist(hist_expected, hist_actual, cv2.HISTCMP_CORREL))

    diff = cv2.absdiff(expected, actual)
    bleed_ratio = float(np.mean(diff > 30))

    degraded = (
        edge_diff_ratio > 1.3
        or hist_corr < HIST_CORR_THRESHOLD
        or bleed_ratio > BLEED_THRESHOLD
    )

    return {
        "degraded": degraded,
        "edge_diff_ratio": round(edge_diff_ratio, 3),
        "hist_correlation": round(hist_corr, 3),
        "bleed_ratio": round(bleed_ratio, 3),
        "confidence": round(
            1.0
            - 0.4 * max(0, edge_diff_ratio - 1.0)
            - 0.3 * max(0, 1.0 - hist_corr)
            - 0.3 * bleed_ratio,
            2,
        ),
    }
