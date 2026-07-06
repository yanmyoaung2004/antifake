# AntiFake v2 — Architecture

## Overview

Version 2 is a focused, demo-ready build for the APICTA competition. It strips away infrastructure dependencies (no Redis, no blockchain, no Docker) and concentrates on the single most impressive feature: **crypto-anchor visual verification** — using a phone camera to detect counterfeit prints by analyzing microscopic noise patterns.

**Stack:** Python/FastAPI + OpenCV + Expo (React Native)

---

## Tools & Libraries

| Layer | Tool | Purpose |
|---|---|---|
| Backend framework | FastAPI + Uvicorn | Async Python HTTP server |
| Computer vision | OpenCV + NumPy | Edge detection, histogram correlation, pixel bleed analysis, heatmap overlay |
| Image processing | Pillow | Image loading and format conversion |
| Mobile | React Native (Expo) | Cross-platform app with camera access |
| Camera | expo-camera | QR scanning + Layer 2 photo capture |
| QR scanning | expo-barcode-scanner | Detect and read QR codes |
| QR generation | qrcode (Python) | Generate Layer 1 QR for printable labels |
| HTTP | axios (mobile), httpx (Python) | API communication |
| Testing | pytest, pytest-asyncio | Unit tests + API roundtrip tests |
| Code quality | ruff | Linting |
| Package management | uv | Python dependency resolution |

---

## Directory Structure

```
version2/
├── plan.md                              # Build plan and concept
├── docs/
│   ├── setup.md                         # Setup instructions
│   ├── test.md                          # Testing guide
│   ├── architecture-version1.md         # v1 architecture reference
│   └── architecture-version2.md         # This file
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI with POST /api/v1/verify
│   │   └── crypto/
│   │       └── anchor.py                # Core CV logic (all functions)
│   ├── tests/
│   │   ├── test_anchor.py               # 8 tests for CV logic + API
│   │   ├── test_samples.py              # 2 tests for pre-generated images
│   │   └── test_verify.py               # 2 tests for API health + roundtrip
│   ├── tools/
│   │   ├── generate_samples.py          # Creates genuine + tampered test PNGs
│   │   └── printable_labels.py          # Creates sticker-ready demo labels
│   ├── sample_images/                   # 6 pre-generated images for testing
│   ├── demo_labels/                     # 2 printable label PNGs for physical demo
│   └── pyproject.toml
└── mobile/
    ├── App.tsx                          # Single-screen app: camera → scan → result
    ├── app.json                         # Expo config with camera permissions
    └── package.json
```

---

## Data Flow

### Single Scan (Verify)

```
Phone Camera                      Backend
    │                                │
    │  Scan QR code                  │
    │  Extract: batch_id|serial      │
    │                                │
    │  Take photo of Layer 2         │
    │  (noise pattern area)          │
    │                                │
    │  POST /api/v1/verify           │
    │  {batch_id, serial,            │
    │   image_base64}                │
    │ ───────────────────────────────>│
    │                                │
    │                                │  seed = f"{batch_id}:{serial}"
    │                                │  expected = generate_anchor(seed)
    │                                │  actual = extract_noise(photo)
    │                                │
    │                                │  compare_anchors(expected, actual):
    │                                │    ├─ Edge sharpness ratio
    │                                │    ├─ Histogram correlation
    │                                │    └─ Pixel bleed ratio
    │                                │
    │                                │  if degraded:
    │                                │    overlay = compute_overlay()
    │                                │
    │  <──────────────────────────────│
    │  {status, confidence,          │
    │   message, metrics,            │
    │   overlay_base64?}             │
    │                                │
    │  Display:                       │
    │  ✅ "AUTHENTIC" (green)         │
    │  or 🚫 "COUNTERFEIT" (red)      │
    │       + heatmap overlay        │
```

---

## Core CV Logic

### `generate_anchor(seed: str) -> np.ndarray`

```
seed = "BATCH-A:001"
      → SHA256(seed)
      → first 8 bytes as int
      → numpy.random.default_rng(int)
      → rng.integers(0, 256, (64, 64))
```

This is **deterministic** — the same seed always produces the exact same noise pattern. The backend can regenerate the expected pattern for any serial without storing images.

### `extract_noise(image_bgr: np.ndarray) -> np.ndarray`

- Converts to grayscale
- If smaller than 64×64, resizes with `INTER_AREA` interpolation
- Crops to top-left 64×64 region

### `compare_anchors(expected, actual) -> dict`

Three independent metrics:

| Metric | Method | Threshold | Weight |
|---|---|---|---|
| **Edge sharpness** | Compares gradient magnitude ratio between expected and actual | `> 1.3` → degraded | 40% |
| **Histogram correlation** | `cv2.compareHist` with `HISTCMP_CORREL` on 32-bin histograms | `< 0.6` → degraded | 30% |
| **Pixel bleed** | Mean of pixels where `|expected - actual| > 30` | `> 0.25` → degraded | 30% |

A sample is marked **degraded** if any metric exceeds its threshold.

Confidence formula:
```
confidence = 1.0
  - 0.4 * max(0, edge_diff_ratio - 1.0)
  - 0.3 * max(0, 1.0 - hist_correlation)
  - 0.3 * bleed_ratio
```

### `compute_overlay(actual, expected) -> np.ndarray`

- Pixel-wise absolute difference
- Normalize to 0–255
- Apply OpenCV `COLORMAP_JET` (blue → cyan → yellow → red)
- Return as base64 PNG

This is the **"wow" visual** — the counterfeit box shows a red heatmap highlighting exactly where the print deviated.

### `simulate_photocopy(anchor, severity=0.3) -> np.ndarray`

Simulates a photocopied counterfeit:
- Gaussian blur (kernel 3×3, sigma 0.5) — softens edges
- Adds random noise — degrades the pattern
- Blends original with degraded at `severity` ratio

Used for generating test images and printable counterfeit labels.

---

## API

### `POST /api/v1/verify`

**Request:**
```json
{
  "batch_id": "BATCH-A",
  "serial": "001",
  "image_base64": "<base64-encoded PNG>"
}
```

**Response (verified):**
```json
{
  "status": "verified",
  "confidence": 1.0,
  "message": "Anchor pattern matches. Authentic.",
  "metrics": {
    "degraded": false,
    "edge_diff_ratio": 1.0,
    "hist_correlation": 1.0,
    "bleed_ratio": 0.0,
    "confidence": 1.0
  },
  "overlay_base64": null
}
```

**Response (counterfeit):**
```json
{
  "status": "counterfeit",
  "confidence": 0.44,
  "message": "Print quality deviation detected. Likely counterfeit.",
  "metrics": {
    "degraded": true,
    "edge_diff_ratio": 1.031,
    "hist_correlation": -0.202,
    "bleed_ratio": 0.608,
    "confidence": 0.44
  },
  "overlay_base64": "<base64-encoded heatmap PNG>"
}
```

### `GET /api/v1/health`

```json
{"status": "ok"}
```

---

## Mobile App Flow

```
┌──────────────────────────────────────┐
│         Home Screen                  │
│  "AntiFake" title                    │
│  "Verify medicine authenticity..."   │
│  [ Start Scan ] button               │
└──────────────┬───────────────────────┘
               │ tap
               ▼
┌──────────────────────────────────────┐
│        Camera Screen                 │
│  ┌──────────────────────────────┐    │
│  │      Camera View             │    │
│  │  Scanning for QR code...     │    │
│  └──────────────────────────────┘    │
│  "Point camera at the QR code"       │
└──────────────┬───────────────────────┘
               │ QR detected
               ▼
┌──────────────────────────────────────┐
│   Loading — "Analyzing..." spinner   │
│   (captures photo, sends to backend) │
└──────────────┬───────────────────────┘
               │ response received
               ▼
┌──────────────────────────────────────┐
│         Result Screen                │
│                                      │
│  ✅ AUTHENTIC (green)               │
│     or 🚫 COUNTERFEIT (red)          │
│                                      │
│  "Anchor pattern matches..."         │
│  Confidence: 100%                    │
│                                      │
│  [Heatmap overlay if counterfeit]    │
│                                      │
│  [ Scan Another ] button             │
└──────────────────────────────────────┘
```

---

## Demo Labels

The `tools/printable_labels.py` script generates 600×400 PNGs ready for sticker paper:

```
┌──────────────────────────────────────┐
│ Batch: BATCH-A  Serial: 001         │
│                                      │
│  ┌──────────┐    ┌──────────┐       │
│  │ Crypto   │    │   QR     │       │
│  │ Anchor   │    │  Code    │       │
│  │ (64×64)  │    │ (240×240)│       │
│  │          │    │          │       │
│  └──────────┘    └──────────┘       │
│                                      │
│  LAYER 2          LAYER 1            │
│  Crypto Anchor    QR Code            │
│                                      │
│          GENUINE or COUNTERFEIT      │
└──────────────────────────────────────┘
```

Print both labels, stick on two identical boxes. One scans as authentic, the other as counterfeit.

---

## Key Differences from v1

| Aspect | v1 | v2 |
|---|---|---|
| Scope | Full supply chain system | Single demo feature |
| Infrastructure | Redis, Docker, Hardhat, blockchain | None — runs on bare Python |
| Anomaly engine | Velocity, density, GPS | Not included |
| Blockchain | Merkle root minting, scan events | Not included |
| Offline support | AsyncStorage queue | Not included |
| Enterprise API | Batch creation with API key | Not included |
| Dependencies | 10+ services | Just Python + Node.js |
| Test count | 19 backend + 6 contracts | 12 backend |
| Setup time | ~1 hour | ~5 minutes |

---

## Testing

See [`test.md`](test.md) for full details.

```bash
cd version2/backend
uv run pytest -v          # 12 tests in under 2 seconds

# Test genuine
python -c "import httpx, base64; print(httpx.post('http://localhost:8000/api/v1/verify', json={'batch_id':'BATCH-A','serial':'001','image_base64':base64.b64encode(open('sample_images/genuine_BATCH-A_001.png','rb').read()).decode()}).json())"

# Test counterfeit
python -c "import httpx, base64; print(httpx.post('http://localhost:8000/api/v1/verify', json={'batch_id':'BATCH-A','serial':'001','image_base64':base64.b64encode(open('sample_images/tampered_BATCH-A_001.png','rb').read()).decode()}).json())"
```
