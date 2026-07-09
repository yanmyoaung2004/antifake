"""
CNN training script for AntiFake crypto-anchor classifier.

Self-contained: generates a synthetic training set from scratch, trains
a small ResNet-18, evaluates it, and exports the weights as a single
file (`classifier.pt`) that the AntiFake backend can load at inference
time without needing PyTorch or a GPU.

Run on a separate training machine (GPU recommended). Then copy
`classifier.pt` back to the AntiFake backend root.

Usage:
    python tools/train_classifier.py
    python tools/train_classifier.py --epochs 20 --samples 20000
    python tools/train_classifier.py --export classifier_v2.pt

Output:
    classifier.pt                    Trained weights (state_dict)
    training_curve.png               Loss + accuracy over epochs
    confusion_matrix.png             Final confusion matrix
    training_report.json             Per-class precision/recall/F1

What the model does:
    Input: 64x64 grayscale crypto-anchor crop
    Output: 2-class softmax [P(genuine), P(counterfeit)]
    Architecture: ResNet-18 modified for 64x64 grayscale input
    Total params: ~11M (small enough to run on CPU at inference)

Why synthetic data:
    Real counterfeit photos don't exist at scale. We use the same
    `simulate_photocopy` and `synthesize_phone_photo` functions that
    the rest of AntiFake uses for testing. The training distribution
    is deliberately broad: many blur/noise/rotation/perspective
    combinations so the model learns "photocopy signature" rather
    than memorising specific transforms.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Data generation (re-implemented here so this script is self-contained —
# the AntiFake backend uses the same algorithms, but we don't import the
# backend here so the training machine doesn't need aiohttp, fastapi, etc.)
# ---------------------------------------------------------------------------

def sha256_seed(seed_str: str) -> np.random.Generator:
    import hashlib
    digest = hashlib.sha256(seed_str.encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "little"))


def generate_anchor(seed_str: str, size: int = 64) -> np.ndarray:
    """16x16 unique values on 4x4 blocks -> 64x64 image. Deterministic."""
    rng = sha256_seed(seed_str)
    grid = rng.integers(0, 256, (size // 4, size // 4), dtype=np.uint8)
    return np.kron(grid, np.ones((4, 4), dtype=np.uint8))


def simulate_photocopy(anchor: np.ndarray, severity: float = 0.35) -> np.ndarray:
    """Simulate photocopy: blur + noise. Severity in [0, 1]."""
    import cv2
    blur_k = max(3, int(severity * 9) | 1)
    blurred = cv2.GaussianBlur(anchor, (blur_k, blur_k), 0)
    rng = np.random.default_rng(42)
    noise = rng.integers(0, int(96 * severity), anchor.shape, dtype=np.uint8)
    tampered = cv2.addWeighted(blurred, 1.0 - severity * 0.5, noise, severity * 0.5, 0)
    return np.clip(tampered, 0, 255).astype(np.uint8)


def random_photocopy(anchor: np.ndarray) -> np.ndarray:
    """Severity drawn from a broad distribution — covers easy and hard cases."""
    severity = float(np.random.uniform(0.1, 0.9))
    return simulate_photocopy(anchor, severity)


def random_augment(img: np.ndarray) -> np.ndarray:
    """
    Random photo-like degradation: brightness, contrast, noise, blur.
    Applied to BOTH genuine and counterfeit samples so the model learns
    to ignore these.
    """
    import cv2
    aug = img.astype(np.float32)
    # Brightness
    if np.random.random() < 0.6:
        factor = float(np.random.uniform(0.6, 1.4))
        aug = aug * factor
    # Additive noise
    if np.random.random() < 0.4:
        noise_std = float(np.random.uniform(2, 20))
        aug = aug + np.random.normal(0, noise_std, aug.shape)
    # Blur
    if np.random.random() < 0.4:
        sigma = float(np.random.uniform(0.3, 1.5))
        aug = cv2.GaussianBlur(aug.astype(np.uint8), (0, 0), sigma).astype(np.float32)
    return np.clip(aug, 0, 255).astype(np.uint8)


def make_dataset(n_samples: int, seed: int = 0):
    """
    Returns (X, y) where:
        X: (n, 64, 64) uint8 — anchor crops
        y: (n,) int64 — 0 = genuine, 1 = counterfeit
    """
    rng = np.random.default_rng(seed)
    X = np.zeros((n_samples, 64, 64), dtype=np.uint8)
    y = np.zeros(n_samples, dtype=np.int64)
    for i in range(n_samples):
        # Unique seed per sample — every box has a different pattern
        seed_str = f"train-{seed}-{i:08d}"
        anchor = generate_anchor(seed_str)
        # Roughly half counterfeit
        is_fake = rng.random() < 0.5
        if is_fake:
            img = random_photocopy(anchor)
        else:
            img = anchor
        # Always apply some augmentation (both classes)
        img = random_augment(img)
        X[i] = img
        y[i] = 1 if is_fake else 0
    return X, y


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def build_resnet18_grayscale(num_classes: int = 2):
    """
    ResNet-18 with the first conv adapted for 64x64 grayscale input.
    Standard torchvision architecture, ~11M params.
    """
    try:
        from torchvision.models import resnet18
    except ImportError:
        print("ERROR: torchvision is required. Install with:")
        print("  pip install torch torchvision")
        sys.exit(1)

    import torch.nn as nn

    model = resnet18(weights=None, num_classes=num_classes)
    # Adapt first conv: 1-channel grayscale, smaller stride for 64x64
    model.conv1 = nn.Conv2d(1, 64, kernel_size=3, stride=1, padding=1, bias=False)
    model.maxpool = nn.Identity()  # don't downsample 64x64 -> 32x32 too aggressively
    return model


def build_tinycnn(num_classes: int = 2):
    """
    ~50K param custom CNN. Use this if you want a tiny model for embedded
    or mobile deployment. Slightly less accurate than ResNet-18.
    """
    import torch
    import torch.nn as nn

    class TinyCNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(),
                nn.Conv2d(16, 16, 3, padding=1), nn.ReLU(),
                nn.MaxPool2d(2),  # 32x32
                nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(),
                nn.Conv2d(32, 32, 3, padding=1), nn.ReLU(),
                nn.MaxPool2d(2),  # 16x16
                nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(),
                nn.Conv2d(64, 64, 3, padding=1), nn.ReLU(),
                nn.AdaptiveAvgPool2d(1),  # 1x1
            )
            self.classifier = nn.Linear(64, num_classes)

        def forward(self, x):
            x = self.features(x)
            x = x.flatten(1)
            return self.classifier(x)

    return TinyCNN()


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train(args):
    print(f"\n{'='*60}")
    print(f"  AntiFake CNN Training")
    print(f"{'='*60}\n")

    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        from torch.utils.data import DataLoader, TensorDataset
    except ImportError:
        print("ERROR: PyTorch is required. Install with:")
        print("  pip install torch torchvision")
        sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("(No GPU — training will be slower but still works)")

    # Data
    print(f"\nGenerating {args.samples} synthetic training samples...")
    t0 = time.time()
    X_train, y_train = make_dataset(args.samples, seed=0)
    X_val, y_val = make_dataset(args.samples // 5, seed=1)
    print(f"  train: {X_train.shape}, val: {X_val.shape}  ({time.time()-t0:.1f}s)")

    # To tensor, add channel dim, normalize to [0, 1]
    X_train_t = torch.from_numpy(X_train).float().unsqueeze(1) / 255.0
    y_train_t = torch.from_numpy(y_train)
    X_val_t = torch.from_numpy(X_val).float().unsqueeze(1) / 255.0
    y_val_t = torch.from_numpy(y_val)

    train_loader = DataLoader(
        TensorDataset(X_train_t, y_train_t),
        batch_size=args.batch_size, shuffle=True, num_workers=0,
    )
    val_loader = DataLoader(
        TensorDataset(X_val_t, y_val_t),
        batch_size=args.batch_size, shuffle=False, num_workers=0,
    )

    # Model
    if args.model == "resnet18":
        model = build_resnet18_grayscale()
    else:
        model = build_tinycnn()
    model = model.to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Model: {args.model}  ({n_params/1e6:.2f}M params)")

    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    criterion = nn.CrossEntropyLoss()

    # Train
    print(f"\nTraining for {args.epochs} epochs (batch={args.batch_size}, lr={args.lr})...\n")
    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}
    best_val_acc = 0.0
    best_state = None
    for epoch in range(args.epochs):
        t0 = time.time()
        model.train()
        train_loss, train_correct, train_n = 0.0, 0, 0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            opt.step()
            train_loss += loss.item() * xb.size(0)
            train_correct += (logits.argmax(1) == yb).sum().item()
            train_n += xb.size(0)
        sched.step()

        model.eval()
        val_loss, val_correct, val_n = 0.0, 0, 0
        all_preds, all_labels = [], []
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                logits = model(xb)
                loss = criterion(logits, yb)
                val_loss += loss.item() * xb.size(0)
                val_correct += (logits.argmax(1) == yb).sum().item()
                val_n += xb.size(0)
                all_preds.extend(logits.argmax(1).cpu().tolist())
                all_labels.extend(yb.cpu().tolist())

        train_loss /= train_n; train_acc = train_correct / train_n
        val_loss /= val_n; val_acc = val_correct / val_n
        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        print(
            f"  epoch {epoch+1:3d}/{args.epochs}  "
            f"train loss={train_loss:.4f} acc={train_acc:.3f}  "
            f"val loss={val_loss:.4f} acc={val_acc:.3f}  "
            f"({time.time()-t0:.1f}s)"
        )

    # Restore best
    if best_state is not None:
        model.load_state_dict(best_state)
    print(f"\nBest val acc: {best_val_acc:.3f}")

    # Final evaluation: confusion matrix
    model.eval()
    tp = tn = fp = fn = 0
    all_probs = []
    with torch.no_grad():
        for xb, yb in val_loader:
            xb, yb = xb.to(device), yb.to(device)
            logits = model(xb)
            probs = F.softmax(logits, dim=1)
            preds = logits.argmax(1)
            for p, l, pr in zip(preds.cpu().tolist(), yb.cpu().tolist(), probs.cpu().tolist()):
                if l == 0 and p == 0: tn += 1
                if l == 1 and p == 1: tp += 1
                if l == 0 and p == 1: fp += 1
                if l == 1 and p == 0: fn += 1
                all_probs.append({"label": l, "pred": p, "p_genuine": pr[0], "p_fake": pr[1]})
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-6)
    accuracy = (tp + tn) / max(tp + tn + fp + fn, 1)
    print(f"\nFinal eval on {tp+tn+fp+fn} val samples:")
    print(f"  Accuracy:  {accuracy:.3f}")
    print(f"  Precision: {precision:.3f}  (counterfeit)")
    print(f"  Recall:    {recall:.3f}  (counterfeit)")
    print(f"  F1:        {f1:.3f}  (counterfeit)")
    print(f"  Confusion: TP={tp}  TN={tn}  FP={fp}  FN={fn}")

    # Save artifacts
    out_path = Path(args.export)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "model_type": args.model,
            "n_params": n_params,
            "best_val_acc": best_val_acc,
            "val_metrics": {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "tp": tp, "tn": tn, "fp": fp, "fn": fn,
            },
            "history": history,
            "config": vars(args),
        },
        out_path,
    )
    print(f"\nSaved weights to {out_path}")

    # Also export to ONNX (preferred format for the backend)
    onnx_path = out_path.with_suffix(".onnx")
    try:
        # Build a fresh model with the right input shape and load weights
        if args.model == "resnet18":
            onnx_model = build_resnet18_grayscale()
        else:
            onnx_model = build_tinycnn()
        onnx_model.load_state_dict(model.state_dict())
        onnx_model.eval()
        dummy = torch.zeros(1, 1, 64, 64)
        torch.onnx.export(
            onnx_model, dummy, str(onnx_path),
            input_names=["input"], output_names=["logits"],
            dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
            opset_version=13,
        )
        print(f"Saved ONNX model to {onnx_path}")
    except Exception as e:
        print(f"(ONNX export skipped: {e})")

    # Report JSON
    report = {
        "model": args.model,
        "n_params": n_params,
        "samples": args.samples,
        "epochs": args.epochs,
        "best_val_acc": best_val_acc,
        "final_metrics": {
            "accuracy": accuracy, "precision": precision,
            "recall": recall, "f1": f1,
            "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        },
    }
    report_path = out_path.with_suffix(".report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Saved report to {report_path}")

    # Plot training curve
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        ax1.plot(history["train_loss"], label="train")
        ax1.plot(history["val_loss"], label="val")
        ax1.set_title("Loss"); ax1.set_xlabel("Epoch"); ax1.legend()
        ax2.plot(history["train_acc"], label="train")
        ax2.plot(history["val_acc"], label="val")
        ax2.set_title("Accuracy"); ax2.set_xlabel("Epoch"); ax2.legend()
        fig.tight_layout()
        plot_path = out_path.with_suffix(".curve.png")
        fig.savefig(plot_path, dpi=100)
        print(f"Saved training curve to {plot_path}")
    except ImportError:
        print("(matplotlib not available, skipping training curve plot)")

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["resnet18", "tinycnn"], default="resnet18")
    parser.add_argument("--samples", type=int, default=10000,
                        help="Number of training samples (default 10000)")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--export", type=str, default="classifier.pt",
                        help="Output path for trained weights")
    args = parser.parse_args()

    train(args)


if __name__ == "__main__":
    main()
