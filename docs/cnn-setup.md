# CNN Classifier Setup

Train a ResNet-18 on synthetic data, then deploy it to the AntiFake backend for real-time inference — no GPU needed on the laptop, just on the training machine.

---

## Overview

```
Your Training Machine (GPU recommended)         AntiFake Laptop (no GPU)
─────────────────────────────                   ────────────────────────
tools/train_classifier.py                       app/ml/classifier.py
  ── generates synthetic dataset                  ── loads classifier.onnx
  ── trains ResNet-18 on 64x64 anchors            ── runs ~5ms per inference
  ── exports classifier.onnx                      ── parallel to hand-tuned CV
        │                                               │
        └─── scp classifier.onnx ──────────────────────>┘
```

The model runs **only on CPU** at inference time. ResNet-18 on 64×64 images is ~5ms per scan — well under the 200ms response budget of the verify endpoint.

---

## Step 1: Set up the training machine

```bash
# Python 3.10+ required
python -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate

pip install torch torchvision numpy opencv-python-headless matplotlib
```

**Optional — GPU acceleration:**

```bash
# For CUDA 12.1
pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision

# For CUDA 11.8
pip install --index-url https://download.pytorch.org/whl/cu118 torch torchvision
```

---

## Step 2: Copy the training script

Copy just `tools/train_classifier.py` from the AntiFake backend. The script is self-contained — it re-implements the data generation so the training machine doesn't need the rest of AntiFake.

```bash
# Create a directory for training
mkdir antifake-training
cd antifake-training

# Copy the single file
cp /path/to/antifake/backend/tools/train_classifier.py .
```

---

## Step 3: Train

```bash
# Default: ResNet-18, 10,000 samples, 10 epochs
python train_classifier.py

# Recommended: 20 epochs, 20,000 samples for best accuracy
python train_classifier.py --epochs 20 --samples 20000

# Tiny CNN (~50K params) for mobile / embedded deployment
python train_classifier.py --model tinycnn

# Custom export path
python train_classifier.py --export ~/Downloads/classifier_v2.onnx
```

**Expected output:**

```
============================================================
  AntiFake CNN Training
============================================================

Device: cuda
GPU: NVIDIA GeForce RTX 3060

Generating 10000 synthetic training samples...
  train: (10000, 64, 64), val: (2000, 64, 64)  (4.2s)

Model: resnet18  (11.17M params)

Training for 10 epochs (batch=64, lr=0.001)...

  epoch   1/10  train loss=0.4521 acc=0.789  val loss=0.3104 acc=0.864  (3.2s)
  epoch   2/10  train loss=0.2310 acc=0.901  val loss=0.1801 acc=0.918  (3.0s)
  ...
  epoch  10/10  train loss=0.0412 acc=0.984  val loss=0.0687 acc=0.973  (3.0s)

Best val acc: 0.973

Final eval on 2000 val samples:
  Accuracy:  0.973
  Precision: 0.970  (counterfeit)
  Recall:    0.976  (counterfeit)
  F1:        0.973  (counterfeit)
  Confusion: TP=976  TN=970  FP=30  FN=24

Saved weights to classifier.pt
Saved ONNX model to classifier.onnx
Saved report to classifier.report.json
Saved training curve to classifier.curve.png
```

Timing on different hardware:

| Hardware | Samples | Epochs | Time |
|---|---|---|---|
| RTX 3060 | 10,000 | 10 | ~3 min |
| RTX 3060 | 20,000 | 20 | ~12 min |
| MacBook M2 (CPU) | 10,000 | 10 | ~20 min |
| Intel i7 (CPU) | 10,000 | 10 | ~35 min |

---

## Step 4: Copy the model to the AntiFake laptop

The only file you need is `classifier.onnx`. Copy it to the AntiFake `backend/` root:

```bash
# From the training machine
scp classifier.onnx user@laptop:/path/to/antifake/backend/

# Or just copy via USB / cloud
```

---

## Step 5: Verify it works

Start the AntiFake server:

```bash
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

Check the model loaded correctly:

```bash
curl http://127.0.0.1:8765/api/v1/model/info
```

Expected:

```json
{
  "ml_available": true,
  "model_path": "/path/to/backend/classifier.onnx",
  "load_error": null
}
```

Run the benchmark to compare CNN vs hand-tuned CV:

```bash
.venv\Scripts\python.exe tools/benchmark.py
```

The benchmark now prints results for both:

```
==================================================
  Accuracy Benchmark Results
==================================================
  Total samples:    100
  Genuine:          50
  Counterfeit:      50

  Hand-tuned CV:
    True positives:   50
    True negatives:   50
    Accuracy:         100.0%

  CNN classifier:
    True positives:   49
    True negatives:   50
    Accuracy:         99.0%
```

If the CNN underperforms, train with more samples or epochs.

---

## How it works at inference

When someone verifies a product with an image, the backend runs both systems in parallel:

```
1. preprocess_photo(photo, expected)  →  64x64 anchor crop
                                          ↓
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
            compare_anchors()      predict_proba()      record_scan()
            (hand-tuned CV)        (CNN classifier)     (hash chain)
                    │                    │
                    └────────┬───────────┘
                             ▼
                    AI Confidence:
                    {p_genuine, p_counterfeit,
                     model, model_agrees_with_cv}
```

- If **either** says counterfeit, the scan is flagged.
- If both say genuine, confidence is high.
- If they disagree (rare), the response includes `model_agrees_with_cv: false` so the UI/chatbot can explain the ambiguity.

---

## Files reference

| File | Location | Purpose |
|---|---|---|
| `train_classifier.py` | `backend/tools/` | Training script (runs on GPU machine) |
| `classifier.onnx` | `backend/` | Trained model weights (copy here after training) |
| `app/ml/__init__.py` | `backend/app/ml/` | Lazy-loads the ONNX model |
| `app/ml/classifier.py` | `backend/app/ml/` | `predict_proba()` inference function |
| `app/ml/explainer.py` | `backend/app/ml/` | Template-based explanation engine |
| `TRAINING.md` | `backend/tools/` | This guide |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: torch` | `pip install torch torchvision` |
| `ModuleNotFoundError: onnxruntime` | Already in dependencies; `uv pip install -e ".[dev]"` |
| Model not loading at startup | Check `classifier.onnx` exists in `backend/` root |
| CNN accuracy < 90% | Train with `--epochs 20 --samples 20000` |
| CNN accuracy > 99% but hand-tuned CV is 100% | Normal — CNN has similar but not identical accuracy |
| Training is very slow on CPU | Use `--model tinycnn` for ~50K param model |
| `classifier.onnx` too large (45MB) | Use `--model tinycnn` (~200KB) or don't include the model |
