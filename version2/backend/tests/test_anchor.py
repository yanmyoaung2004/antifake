import base64

import cv2
import numpy as np
from httpx import ASGITransport, AsyncClient
import pytest

from app.crypto.anchor import generate_anchor, compare_anchors, extract_noise
from app.main import app


class TestGenerateAnchor:
    def test_same_seed_produces_same_pattern(self):
        a = generate_anchor("BATCH-A:001")
        b = generate_anchor("BATCH-A:001")
        np.testing.assert_array_equal(a, b)

    def test_different_seeds_produce_different_patterns(self):
        a = generate_anchor("BATCH-A:001")
        b = generate_anchor("BATCH-A:002")
        assert not np.array_equal(a, b)

    def test_output_is_correct_shape(self):
        result = generate_anchor("BATCH-A:001")
        assert result.shape == (64, 64)
        assert result.dtype == np.uint8


class TestCompareAnchors:
    def test_identical_anchors_pass(self):
        anchor = generate_anchor("BATCH-A:001")
        result = compare_anchors(anchor, anchor)
        assert result["degraded"] is False
        assert result["confidence"] >= 0.9

    def test_different_anchors_flag(self):
        expected = generate_anchor("BATCH-A:001")
        actual = generate_anchor("BATCH-A:002")
        result = compare_anchors(expected, actual)
        assert result["degraded"] is True

    def test_noisy_image_flags(self):
        expected = generate_anchor("BATCH-A:001")
        rng = np.random.default_rng(42)
        noise = rng.integers(0, 256, (64, 64), dtype=np.uint8)
        result = compare_anchors(expected, noise)
        assert result["degraded"] is True


class TestVerifyEndpoint:
    def _make_request(self, image_b64: str):
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_valid_anchor_returns_verified(self):
        anchor = generate_anchor("BATCH-A:001")
        _, buf = cv2.imencode(".png", anchor)
        b64 = base64.b64encode(buf.tobytes()).decode()

        async with self._make_request(b64) as client:
            resp = await client.post(
                "/api/v1/verify",
                json={"batch_id": "BATCH-A", "serial": "001", "image_base64": b64},
            )
        data = resp.json()
        assert data["status"] == "verified"
        assert data["confidence"] >= 0.9

    @pytest.mark.asyncio
    async def test_tampered_anchor_returns_counterfeit(self):
        anchor = generate_anchor("BATCH-A:001")
        rng = np.random.default_rng(99)
        noise = rng.integers(0, 100, (64, 64), dtype=np.uint8)
        tampered = cv2.addWeighted(anchor, 0.5, noise, 0.5, 0)
        _, buf = cv2.imencode(".png", tampered)
        b64 = base64.b64encode(buf.tobytes()).decode()

        async with self._make_request(b64) as client:
            resp = await client.post(
                "/api/v1/verify",
                json={"batch_id": "BATCH-A", "serial": "001", "image_base64": b64},
            )
        data = resp.json()
        assert data["status"] == "counterfeit"
