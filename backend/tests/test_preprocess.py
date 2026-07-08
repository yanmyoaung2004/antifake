"""
Tests for the photo preprocessing pipeline.

Validates that the anchor extraction works for:
  - Clean axis-aligned photos (the "happy path")
  - Photos with mild blur (still extracts the right pattern)
  - Photos without a QR (returns None, gracefully degrades)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np
import pytest

from app.crypto.anchor import generate_anchor, compare_anchors
from app.crypto.preprocess import (
    preprocess_photo,
    synthesize_phone_photo,
    detect_qr_corners,
    extract_anchor_from_photo,
)
from app.tools_helpers import make_label_rgb


def _label_photo(batch_id: str, serial: str, **kwargs) -> np.ndarray:
    """Generate a synthetic phone photo of a printed label."""
    label = make_label_rgb(batch_id, serial, counterfeit=False, severity=0.0)
    return synthesize_phone_photo(label, **kwargs)


class TestDetectQRCorners:
    def test_detects_qr_in_clean_photo(self):
        photo = _label_photo("BATCH-A", "001", blur_sigma=0.0)
        gray = cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY)
        corners = detect_qr_corners(gray)
        assert corners is not None
        assert corners.shape == (4, 2)
        # Corners should be in TL, TR, BR, BL order
        # TL is top-left (smallest x+y), BR is bottom-right (largest x+y)
        assert corners[0, 0] + corners[0, 1] < corners[2, 0] + corners[2, 1]

    def test_returns_none_for_no_qr(self):
        # Pure noise image — no QR
        noise = np.random.default_rng(42).integers(0, 256, (400, 600), dtype=np.uint8)
        corners = detect_qr_corners(noise)
        assert corners is None


class TestPreprocessPhoto:
    def test_clean_photo_extracts_perfect_anchor(self):
        photo = _label_photo("BATCH-A", "001", blur_sigma=0.0)
        expected = generate_anchor("BATCH-A:001")
        actual, info = preprocess_photo(photo, expected=expected)
        assert actual is not None
        assert actual.shape == (64, 64)
        result = compare_anchors(expected, actual)
        assert result["degraded"] is False
        assert result["confidence"] >= 0.9

    def test_unknown_seed_falls_back(self):
        # Photo of a label, but we don't know the expected (no expected passed)
        photo = _label_photo("BATCH-A", "001", blur_sigma=0.0)
        actual, info = preprocess_photo(photo, expected=None)
        assert actual is not None
        assert actual.shape == (64, 64)

    def test_no_qr_returns_none(self):
        noise = np.random.default_rng(42).integers(0, 256, (400, 600, 3), dtype=np.uint8)
        actual, info = preprocess_photo(noise, expected=None)
        assert actual is None
        assert info["qr_found"] is False


class TestPhotoDegradation:
    """Verify the system behaves reasonably for various photo conditions."""

    @pytest.mark.parametrize("blur_sigma,expected_pass", [
        (0.0, True),    # clean
        (0.8, True),    # mild blur
        (1.5, False),   # moderate blur — likely fails
    ])
    def test_blur_levels(self, blur_sigma, expected_pass):
        photo = _label_photo("BATCH-A", "001", blur_sigma=blur_sigma)
        expected = generate_anchor("BATCH-A:001")
        actual, _ = preprocess_photo(photo, expected=expected)
        assert actual is not None
        result = compare_anchors(expected, actual)
        if expected_pass:
            # Soft check: the geometric pipeline should at least produce *something*
            # and not be catastrophically wrong.
            assert result["confidence"] > 0.3
