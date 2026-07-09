# Training the AntiFake CNN Classifier

This guide walks you through training a small CNN that classifies
crypto-anchor crops as **genuine** or **counterfeit**. The model
replaces (or augments) the hand-tuned CV thresholds in the AntiFake
backend.

You can train on a separate machine — the only thing the backend needs
afterwards is the exported weights file (`classifier.pt`).

---

## 1. What you're training

| Property | Value |
|---|---|
| Task | Binary classification: genuine vs. counterfeit |
| Input | 64×64 grayscale crypto-anchor crop |
| Output | 2-class softmax: `P(genuine)`, `P(counterfeit)` |
| Default model | ResNet-18 (modified for 64×64 grayscale) — ~11M params |
| Alternative | TinyCNN — ~50K params (for mobile / embedded) |
| Training data | Synthetic: `simulate_photocopy` + photo augmentation |
| Default training | 10,000 samples × 10 epochs (≈ 10 min on GPU, 30 min on CPU) |

The training data is **synthetic**: every sample is generated from
the same `simulate_photocopy` and `random_augment` functions that
the backend uses for testing. The augmentation pipeline is broad on
purpose (blur σ ∈ [0.3, 1.5], noise σ ∈ [2, 20], brightness ∈ [0.6, 1.4])
so the model learns the *photocopy signature* (loss of block edges +
noise + histogram shift) rather than memorising specific transforms.

**Translation augmentation (critical):** 70% of samples receive a
random 1-4 pixel shift on both axes. This simulates the QR detection
jitter that causes the geometric preprocessing pipeline to misalign
the crop by 1-2 pixels. The model learns to recognize the block
pattern even when shifted, which is the #1 failure mode on real
phone photos.

**Rotation augmentation:** 30% of samples receive a random ±8°
rotation, simulating a phone camera held at a slight angle to the
label.

---

## 2. Set up the training machine

The training script needs Python 3.10+, PyTorch, and a few basics.
CPU works fine for the default config; GPU is faster.

```bash
# On the training machine
git clone <your repo>    # or copy the backend/ folder
cd antifake/backend

python -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows

pip install torch torchvision numpy opencv-python-headless matplotlib
```

That's it. No need to install the rest of the AntiFake backend
(FastAPI, aiosqlite, etc.) — `train_classifier.py` is self-contained.

### GPU (optional but recommended)

If you have an NVIDIA GPU:

```bash
pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision
```

The script auto-detects CUDA. On a typical laptop GPU (e.g., RTX 3060)
10 epochs takes ~3 minutes. On CPU it's ~30 minutes.

---

## 3. Train

```bash
# Default: ResNet-18, 10k samples, 10 epochs, exports to classifier.pt
python tools/train_classifier.py

# Longer training for better accuracy
python tools/train_classifier.py --epochs 20 --samples 20000

# Tiny CNN for mobile deployment (~50K params, slightly less accurate)
python tools/train_classifier.py --model tinycnn

# Custom export path
python tools/train_classifier.py --export classifier_v2.pt
```

Sample output (truncated):

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
...
Saved weights to classifier.pt
```

---

## 4. Copy back to the AntiFake backend

The script produces four artifacts:

| File | What it is | Need on backend? |
|---|---|---|
| `classifier.pt` | Trained weights + metadata | **Yes** |
| `classifier.report.json` | Final accuracy / F1 / confusion | No (for your records) |
| `classifier.curve.png` | Loss + accuracy plot | No (for your records) |
| (no confusion matrix file in this version — printed to stdout) | | |

Copy just `classifier.pt` to the AntiFake backend root:

```bash
# From the training machine
scp classifier.pt user@laptop:~/antifake/backend/

# Or use a USB stick, cloud sync, whatever.
```

The backend will auto-detect `classifier.pt` on startup and use it.
If the file is missing, the backend falls back to the hand-tuned CV
(no degradation — the AI layer is purely additive).

---

## 5. Verify it works

On the AntiFake laptop (with the model in place):

```bash
cd backend
.venv\Scripts\python.exe tools/benchmark.py
```

You should see a new section comparing hand-tuned CV vs CNN accuracy:

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
    True positives:   50
    True negatives:   49
    Accuracy:         99.0%
```

If the CNN underperforms the hand-tuned CV, try:
- More samples: `--samples 20000`
- More epochs: `--epochs 20`
- Bigger model: `resnet18` (default) is already the largest option

If it still underperforms, the most likely cause is **domain mismatch
between your augmentation pipeline and the real photos** the verifier
will see. Open `random_augment` in the training script and tune the
ranges to match your real-world conditions.

---

## 6. What the model sees at inference

The AntiFake backend runs the CNN as part of `/api/v1/verify`:

```json
{
  "status": "verified",
  "ai_confidence": {
    "p_genuine": 0.998,
    "p_counterfeit": 0.002,
    "model": "resnet18",
    "model_agrees_with_cv": true
  },
  "metrics": { ... hand-tuned CV metrics ... }
}
```

`model_agrees_with_cv` is `true` when the CNN and the hand-tuned CV
reach the same verdict. When they disagree, both are returned so the
UI can show a "low confidence — second opinion" state.

The CNN does **not** replace the hand-tuned CV — both run in parallel.
The hand-tuned metrics are the authoritative signal; the CNN is an
independent second opinion. If either says "counterfeit", the system
flags the scan.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: torch` | `pip install torch torchvision` |
| `CUDA out of memory` | Reduce `--batch-size` to 32 or 16 |
| CNN accuracy way below hand-tuned CV | More `--epochs` and `--samples`; check augmentation ranges |
| Training is very slow | Install CUDA-enabled PyTorch, or use `--model tinycnn` |
| `FileNotFoundError: classifier.pt` at backend startup | Backend works fine without it — falls back to hand-tuned CV. Copy the file when you have it. |
| Model file is too large to ship | Use `--model tinycnn` (50K params, ~200KB) instead of ResNet-18 (~45MB) |

---

## Files

- `tools/train_classifier.py` — the training script (self-contained)
- `app/ml/classifier.py` — backend inference module (uses the trained weights)
- `app/main.py` — `/api/v1/verify` now returns `ai_confidence` alongside `metrics`
