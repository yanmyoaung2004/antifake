"""
CNN classifier for crypto-anchor verification.

Loads a trained ONNX model (`classifier.onnx` in the backend root) and
runs inference on 64x64 anchor crops. Returns per-class probabilities
(genuine / counterfeit) that the verify endpoint exposes as
`ai_confidence` in its response.

The classifier is **additive** — it runs in parallel with the
hand-tuned CV (`compare_anchors`). If either signals counterfeit, the
scan is flagged. The hand-tuned CV is the authoritative signal; the
CNN is an independent second opinion that's particularly useful when
the hand-tuned metrics are ambiguous (e.g., edge ratio at 0.68,
right at the threshold).

If `classifier.onnx` is missing, the module is inert and
`predict()` returns `None`. The backend falls back to hand-tuned CV
alone — no degradation in behaviour.

ONNX runtime notes:
    onnxruntime is ~50MB (vs ~200MB for full PyTorch), and CPU
    inference for ResNet-18 on 64x64 is ~5ms — well under the verify
    endpoint's typical latency budget. No GPU required.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import numpy as np

# Lazy-loaded so the backend doesn't need onnxruntime installed for
# the rest of the app to work. If the model file is missing, we
# never import onnxruntime.
_MODEL = None
_MODEL_PATH: Optional[Path] = None
_MODEL_LOAD_ERROR: Optional[str] = None


def _candidate_paths() -> list[Path]:
    """Locations to look for the model, in priority order."""
    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent.parent / "classifier.onnx",  # backend/classifier.onnx
        here.parent.parent / "classifier.onnx",          # backend/app/classifier.onnx
        Path.cwd() / "classifier.onnx",                  # cwd-relative
    ]
    return candidates


def _load_model():
    """Load the ONNX model once, then cache it."""
    global _MODEL, _MODEL_PATH, _MODEL_LOAD_ERROR
    if _MODEL is not None or _MODEL_LOAD_ERROR is not None:
        return _MODEL
    try:
        import onnxruntime as ort
    except ImportError as e:
        _MODEL_LOAD_ERROR = f"onnxruntime not installed: {e}"
        return None

    for path in _candidate_paths():
        if path.exists():
            try:
                _MODEL = ort.InferenceSession(
                    str(path),
                    providers=["CPUExecutionProvider"],
                )
                _MODEL_PATH = path
                return _MODEL
            except Exception as e:
                _MODEL_LOAD_ERROR = f"failed to load {path}: {e}"
                return None
    _MODEL_LOAD_ERROR = "classifier.onnx not found (hand-tuned CV only)"
    return None


def is_available() -> bool:
    """True if a trained model is loaded and ready for inference."""
    return _load_model() is not None


def model_path() -> Optional[str]:
    """Path to the loaded model, or None."""
    _load_model()
    return str(_MODEL_PATH) if _MODEL_PATH else None


def load_error() -> Optional[str]:
    """Reason the model isn't available, or None if it is."""
    _load_model()
    return _MODEL_LOAD_ERROR


def predict_proba(anchor_64x64: np.ndarray) -> Optional[dict]:
    """
    Run the CNN on a 64x64 grayscale anchor.

    Args:
        anchor_64x64: uint8 array, shape (64, 64). One channel, no batch dim.

    Returns:
        dict with keys:
            p_genuine: P(genuine) ∈ [0, 1]
            p_counterfeit: P(counterfeit) ∈ [0, 1]
            model: model name (e.g., "resnet18")
        or None if no model is loaded.
    """
    sess = _load_model()
    if sess is None:
        return None
    if anchor_64x64.shape != (64, 64):
        # Resize defensively — the pipeline should always pass 64x64
        import cv2
        anchor_64x64 = cv2.resize(anchor_64x64, (64, 64), interpolation=cv2.INTER_AREA)
    # Normalize to [0, 1] and add batch + channel dims
    x = anchor_64x64.astype(np.float32) / 255.0
    x = x[np.newaxis, np.newaxis, :, :]  # (1, 1, 64, 64)
    input_name = sess.get_inputs()[0].name
    logits = sess.run(None, {input_name: x})[0][0]
    # Softmax
    e = np.exp(logits - logits.max())
    probs = e / e.sum()
    return {
        "p_genuine": float(probs[0]),
        "p_counterfeit": float(probs[1]),
        "model": sess.get_inputs()[0].name or "cnn",
    }
