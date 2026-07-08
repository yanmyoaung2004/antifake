"""
Real-world photo simulation: tests the full pipeline (preprocess + compare)
against synthetic phone photos of the printable label, with realistic
degradations (blur, angle, perspective, lighting, noise).
"""
import base64
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np

from app.crypto.anchor import generate_anchor, compare_anchors
from app.crypto.preprocess import synthesize_phone_photo
from app.tools_helpers import make_label_rgb


def make_label_pil(batch_id: str, serial: str, counterfeit: bool = False, severity: float = 0.35):
    from PIL import Image
    return make_label_rgb(batch_id, serial, counterfeit, severity, as_pil=True)


def encode_b64(img: np.ndarray) -> str:
    _, buf = cv2.imencode(".png", img)
    return base64.b64encode(buf.tobytes()).decode()


def full_pipeline(image_bgr: np.ndarray, batch_id: str, serial: str) -> dict:
    from app.crypto.preprocess import preprocess_photo
    expected = generate_anchor(f"{batch_id}:{serial}")
    actual, pp_info = preprocess_photo(image_bgr, expected=expected)
    if actual is None:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if image_bgr.ndim == 3 else image_bgr
        actual = cv2.resize(gray, (64, 64))
    return compare_anchors(expected, actual), pp_info


def run_scenarios():
    print(f"\n{'='*70}")
    print(f"  Real-Phone-Photo Robustness Test (preprocessing pipeline)")
    print(f"{'='*70}")

    scenarios = [
        ("Perfect scan (no degradation)",     dict(blur_sigma=0.0, rotation_deg=0.0, perspective_strength=0.0, brightness=1.0, noise=0.0)),
        ("Phone photo: mild blur",            dict(blur_sigma=0.8, rotation_deg=0.0, perspective_strength=0.0, brightness=1.0, noise=0.0)),
        ("Phone photo: moderate blur",        dict(blur_sigma=1.5, rotation_deg=0.0, perspective_strength=0.0, brightness=1.0, noise=0.0)),
        ("Phone photo: angled 5deg",          dict(blur_sigma=0.8, rotation_deg=5.0, perspective_strength=0.05, brightness=1.0, noise=0.0)),
        ("Phone photo: angled 10deg",         dict(blur_sigma=0.8, rotation_deg=10.0, perspective_strength=0.08, brightness=1.0, noise=0.0)),
        ("Phone photo: angled 15deg",         dict(blur_sigma=0.8, rotation_deg=15.0, perspective_strength=0.10, brightness=1.0, noise=0.0)),
        ("Low light phone photo",             dict(blur_sigma=0.8, rotation_deg=2.0, perspective_strength=0.03, brightness=0.5, noise=0.05)),
        ("Bright light phone photo",          dict(blur_sigma=0.8, rotation_deg=2.0, perspective_strength=0.03, brightness=1.3, noise=0.0)),
        ("Noisy low-light photo",             dict(blur_sigma=0.8, rotation_deg=2.0, perspective_strength=0.03, brightness=0.7, noise=0.15)),
        ("Hand tremor: heavy blur",           dict(blur_sigma=2.5, rotation_deg=2.0, perspective_strength=0.03, brightness=1.0, noise=0.0)),
        ("Photocopy: mild degradation",       dict(blur_sigma=0.8, rotation_deg=2.0, perspective_strength=0.03, brightness=1.0, noise=0.25)),
        ("Photocopy: heavy degradation",      dict(blur_sigma=0.8, rotation_deg=2.0, perspective_strength=0.03, brightness=1.0, noise=0.5)),
        ("Photocopy + perspective",           dict(blur_sigma=0.8, rotation_deg=8.0, perspective_strength=0.10, brightness=1.0, noise=0.4)),
    ]

    genuine_pass = 0
    fake_caught = 0
    for i, (label, params) in enumerate(scenarios):
        ser = f"PHOTO{i:02d}"
        # Genuine: simulate a phone photo of a genuine printed label
        label_img = make_label_pil("BATCH-A", ser, counterfeit=False, severity=0.0)
        photo = synthesize_phone_photo(np.array(label_img), **params)
        result, info = full_pipeline(photo, "BATCH-A", ser)
        genuine_ok = not result["degraded"]
        if genuine_ok:
            genuine_pass += 1
        mark = "PASS" if genuine_ok else "FAIL"
        print(f"  [{mark}] genuine  {label:42s}  conf:{result['confidence']:.0%}  qr:{info.get('qr_found')}")

        # Counterfeit: photocopy simulation embedded in the label itself
        fake_label = make_label_pil("BATCH-A", ser, counterfeit=True, severity=0.45)
        fake_photo = synthesize_phone_photo(np.array(fake_label), **params)
        result2, info2 = full_pipeline(fake_photo, "BATCH-A", ser)
        fake_ok = result2["degraded"]
        if fake_ok:
            fake_caught += 1
        mark2 = "CATCH" if fake_ok else "MISS"
        print(f"  [{mark2}] fake     {label:42s}  conf:{result2['confidence']:.0%}  qr:{info2.get('qr_found')}")

    print(f"{'='*70}")
    total = len(scenarios)
    print(f"  Genuine correctly verified: {genuine_pass}/{total}  ({genuine_pass/total*100:.0f}%)")
    print(f"  Counterfeit correctly caught: {fake_caught}/{total}  ({fake_caught/total*100:.0f}%)")
    print(f"{'='*70}")


if __name__ == "__main__":
    run_scenarios()
