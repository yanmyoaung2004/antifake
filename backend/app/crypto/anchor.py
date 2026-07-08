"""
Crypto-anchor comparison.

The anchor is a deterministic 16x16 noise pattern, each cell rendered as
a 4x4 block of equal pixels (so the printed anchor is 64x64 with only
16x16 unique values). This coarse structure survives mild camera blur
and small perspective warps; only heavy photocopy degradation flattens
the block edges enough to be detected.

Why coarse: 64x64 of pure random noise has Nyquist frequency at 32
cycles, and even σ=0.8 blur (in the 600x400 label) attenuates most of
that. With 16x16 unique values on 4x4 blocks, the highest "frequency"
is 8 cycles across the anchor — well below the blur's cutoff.

Comparison metrics:
  - block_similarity: NCC on downsampled 16x16 (blur-invariant)
  - fft_correlation: frequency-domain match (catches overall structure)
  - hist_correlation: noise histogram shape
  - bleed_ratio: fraction of pixels with diff > 30 (catches heavy damage)
  - edge_sharpness_ratio: edge count vs expected (catches print loss)

A label is "degraded" if multiple metrics fail simultaneously, which
indicates photocopy-like signature rather than normal photo degradation.
"""
from __future__ import annotations

import hashlib

import cv2
import numpy as np

ANCHOR_SIZE = 64
ANCHOR_GRID = 16  # 16x16 unique values, each rendered as 4x4 block

# Tuned for real-world phone photos.
HIST_CORR_THRESHOLD = 0.30
FFT_CORR_THRESHOLD = 0.30
BLEED_THRESHOLD = 0.40
BLOCK_NCC_THRESHOLD = 0.50
EDGE_RATIO_THRESHOLD = 0.70  # below this = significant edge loss


def generate_anchor(seed: str) -> np.ndarray:
    """Return a 64x64 anchor with a 16x16 noise pattern, each cell as 4x4 block."""
    digest = hashlib.sha256(seed.encode()).digest()
    rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
    grid = rng.integers(0, 256, (ANCHOR_GRID, ANCHOR_GRID), dtype=np.uint8)
    return np.kron(grid, np.ones((4, 4), dtype=np.uint8))


def extract_noise(image: np.ndarray) -> np.ndarray:
    """Legacy fallback: top-left crop. Used when no QR is detected."""
    size = ANCHOR_SIZE
    h, w = image.shape
    if h < size or w < size:
        image = cv2.resize(image, (size, size), interpolation=cv2.INTER_AREA)
    return image[:size, :size]


def _fft_log_magnitude(gray: np.ndarray) -> np.ndarray:
    """Log-scaled FFT magnitude, shift DC to center, normalized to [0, 1]."""
    f = np.fft.fft2(gray.astype(np.float32))
    fshift = np.fft.fftshift(f)
    mag = np.log1p(np.abs(fshift))
    mag = (mag - mag.min()) / max(mag.max() - mag.min(), 1e-6)
    return mag


def _downsample_blocks(gray: np.ndarray) -> np.ndarray:
    """Reduce 64x64 to 16x16 by averaging each 4x4 block."""
    return gray.reshape(ANCHOR_GRID, 4, ANCHOR_GRID, 4).mean(axis=(1, 3))


def compare_anchors(expected: np.ndarray, actual: np.ndarray) -> dict:
    if expected.shape != actual.shape:
        actual = cv2.resize(actual, (expected.shape[1], expected.shape[0]))

    hist_expected = cv2.calcHist([expected], [0], None, [32], [0, 256])
    hist_actual = cv2.calcHist([actual], [0], None, [32], [0, 256])
    cv2.normalize(hist_expected, hist_expected)
    cv2.normalize(hist_actual, hist_actual)
    hist_corr = float(cv2.compareHist(hist_expected, hist_actual, cv2.HISTCMP_CORREL))

    fft_e = _fft_log_magnitude(expected)
    fft_a = _fft_log_magnitude(actual)
    e_flat = fft_e.flatten() - fft_e.mean()
    a_flat = fft_a.flatten() - fft_a.mean()
    denom = np.sqrt((e_flat * e_flat).sum() * (a_flat * a_flat).sum()) + 1e-6
    fft_corr = float((e_flat * a_flat).sum() / denom)

    # Block-level NCC: average each 4x4 block to 16x16, then NCC. This
    # is robust to mild blur and small perspective shifts.
    e_grid = _downsample_blocks(expected)
    a_grid = _downsample_blocks(actual)
    e_flat = e_grid.flatten().astype(np.float32) - e_grid.mean()
    a_flat = a_grid.flatten().astype(np.float32) - a_grid.mean()
    denom = np.sqrt((e_flat * e_flat).sum() * (a_flat * a_flat).sum()) + 1e-6
    block_ncc = float((e_flat * a_flat).sum() / denom)

    # Block-edge sharpness: the expected pattern has SHARP transitions
    # between 4x4 blocks. A photocopy / scan loses these sharp edges
    # because the print+scan process is a low-pass filter on the blocks.
    # We measure the gradient magnitude along the block boundaries
    # (rows 3-4, 7-8, ... and columns 3-4, 7-8, ...). High = sharp edges.
    gx = cv2.Sobel(actual, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(actual, cv2.CV_32F, 0, 1, ksize=3)
    g = np.sqrt(gx * gx + gy * gy)
    # Sample at block boundaries: every 4th row/column, offset by 3
    boundary_rows = [3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51, 55, 59]
    boundary_cols = boundary_rows
    edge_sharpness = float(
        g[boundary_rows, :].mean() + g[:, boundary_cols].mean()
    ) / 2.0
    # Compare to expected's edge sharpness
    egx = cv2.Sobel(expected, cv2.CV_32F, 1, 0, ksize=3)
    egy = cv2.Sobel(expected, cv2.CV_32F, 0, 1, ksize=3)
    eg = np.sqrt(egx * egx + egy * egy)
    expected_sharpness = float(
        eg[boundary_rows, :].mean() + eg[:, boundary_cols].mean()
    ) / 2.0
    edge_ratio = edge_sharpness / max(expected_sharpness, 1.0)

    diff = cv2.absdiff(expected, actual)
    bleed_ratio = float(np.mean(diff > 30))

    edges_expected = cv2.Canny(expected, 50, 150)
    edges_actual = cv2.Canny(actual, 50, 150)
    edge_diff_ratio = float(np.sum(edges_actual > 0) / max(np.sum(edges_expected > 0), 1))

    # Photocopies: low edge sharpness (blur of blocks), high bleed.
    # Wrong batch (different seed): high edge sharpness but low block_ncc.
    # Pure noise: low edge sharpness AND low block_ncc.
    # Genuine: high edge sharpness AND high block_ncc.
    degraded = (
        block_ncc < 0.30
        or (edge_ratio < EDGE_RATIO_THRESHOLD and (bleed_ratio > 0.35 or hist_corr < 0.2))
    )

    confidence = round(
        max(0.0, min(1.0,
            0.35 * max(0.0, (block_ncc + 1) / 2)
            + 0.25 * min(1.0, edge_ratio)
            + 0.20 * max(0.0, hist_corr)
            + 0.10 * max(0.0, (fft_corr + 1) / 2)
            + 0.10 * max(0.0, 1.0 - bleed_ratio)
        )),
        2,
    )

    return {
        "degraded": degraded,
        "hist_correlation": round(hist_corr, 3),
        "fft_correlation": round(fft_corr, 3),
        "block_ncc": round(block_ncc, 3),
        "edge_sharpness": round(edge_sharpness, 2),
        "edge_ratio": round(edge_ratio, 3),
        "bleed_ratio": round(bleed_ratio, 3),
        "edge_diff_ratio": round(edge_diff_ratio, 3),
        "confidence": confidence,
    }


def compute_overlay(actual: np.ndarray, expected: np.ndarray) -> np.ndarray:
    diff = cv2.absdiff(expected, actual)
    diff_norm = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
    heatmap = cv2.applyColorMap(diff_norm, cv2.COLORMAP_JET)
    return heatmap


def simulate_photocopy(anchor: np.ndarray, severity: float = 0.3) -> np.ndarray:
    """
    Simulate photocopy degradation.

    Real photocopies: heavy blur (low-pass) + new noise from the scan
    process. For block-based anchors, the blur destroys the 4x4 block
    edges (each block becomes a soft gradient rather than a sharp step).
    """
    # Heavy blur (destroy block edges)
    blur_k = max(3, int(severity * 9) | 1)  # odd kernel size
    blurred = cv2.GaussianBlur(anchor, (blur_k, blur_k), 0)
    # Add scan noise
    rng = np.random.default_rng(42)
    noise = rng.integers(0, int(96 * severity), anchor.shape, dtype=np.uint8)
    tampered = cv2.addWeighted(blurred, 1.0 - severity * 0.5, noise, severity * 0.5, 0)
    return np.clip(tampered, 0, 255).astype(np.uint8)
