# AntiFake — Project Status

**Last updated:** July 2026  
**Total commits:** 42 (on main)  
**Total tests:** 35, all passing  
**Target competition:** APICTA  

---

## 1. What Is AntiFake

A phone can detect counterfeit medicine without any special hardware — just a batch number and a camera.

AntiFake combines three independent verification layers:

| Layer | What it does | Requires factory? | Works today? |
|---|---|---|---|
| **Spatial-Temporal** | Velocity, density, GPS region checks on any batch/serial | No | Yes |
| **Crypto-Anchor CV** | Visual noise pattern (16x16 blocks on 4x4 pixels) | Yes (print anchor) | Yes |
| **Hash Chain** | SHA256 cryptographic audit trail per serial | No | Yes |
| **AI Classifier** | CNN (ResNet-18) second opinion on anchor photos | Yes (print anchor) | Needs training |

**Key design decision:** The system works with just a batch number (no image, no factory cooperation). The CV and AI layers are optional bonuses that activate when the factory prints a crypto-anchor.

---

## 2. Architecture

### 2.1 Request Flow

```
Phone Browser / PWA
    │
    │  POST /api/v1/verify
    │  {batch_id, serial, image_base64?, lat, lng, timestamp}
    ▼
FastAPI Server (app/main.py)
    │
    ├── 1. Crypto-Anchor CV (if image provided)
    │   ├── generate_anchor(seed) → 64x64 block noise (deterministic)
    │   ├── preprocess_photo(img, expected) → QR detect → crop → NCC refine
    │   └── compare_anchors(expected, actual) → block NCC, edge ratio, hist, FFT, bleed
    │
    ├── 2. AI Classifier (if classifier.onnx present)
    │   └── predict_proba(64x64 crop) → {p_genuine, p_counterfeit}
    │
    ├── 3. Spatial-Temporal Checks (always runs)
    │   ├── Velocity: Haversine distance / time delta > 120 km/h
    │   ├── Density: scan count + 1 > 3 → replay alert
    │   └── GPS: scan location outside batch's region bounds
    │
    ├── 4. Hash Chain (always runs)
    │   └── SHA256(serial|batch|lat|lng|timestamp|result|prev_hash)
    │
    └── Response: {status, confidence, message, metrics,
                   overlay_base64?, batch_info, scan_history, ai_confidence?}
```

### 2.2 Status Determination

| Status | When | User sees |
|---|---|---|
| `verified` | All checks pass | ✅ Green badge, "No anomalies detected" |
| `counterfeit` | CV or AI says fake | 🚫 Red badge, heatmap overlay |
| `flagged` | Spatial-temporal alert (velocity/density/GPS) | ⚠️ Yellow badge, specific alert |
| `error` | Exception | ⚠️ Error badge, error message |

### 2.3 Data Flow Diagram

```
                          Phone Camera
                              │
                              ▼
                  ┌──────────────────────┐
                  │  web/index.html       │
                  │  PWA (Service Worker) │
                  │  Leaflet.js Map       │
                  │  jsQR Scanner (HTTPS) │
                  │  GPS geolocation      │
                  │  AI Pharmacist Chat   │
                  └──────┬───────────────┘
                         │ POST /api/v1/*
                         ▼
                  ┌──────────────────────┐
                  │  FastAPI Server       │
                  │  app/main.py          │
                  └──────┬───────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ SQLite   │   │ OpenCV   │   │ ONNX     │
   │ aiosqlite│   │ NumPy    │   │ Runtime  │
   │          │   │          │   │ (opt)    │
   │ batches  │   │ anchor   │   │ CNN      │
   │ routes   │   │ preproc  │   │ classif. │
   │ scans    │   │          │   │          │
   │ chain    │   │          │   │          │
   └──────────┘   └──────────┘   └──────────┘
```

---

## 3. Directory Structure (Full)

```
antifake/
├── .gitignore
├── plan.md                       # Original build plan (historical)
├── CHANGELOG.md                  # Changes by phase
├── status.md                     # This file
├── README.md                     # Public-facing summary
│
├── backend/                      # Python + FastAPI backend (main app)
│   ├── pyproject.toml            # Dependencies, build config
│   ├── uv.lock                   # Locked dependency versions
│   ├── antifake.db               # SQLite DB (gitignored, auto-created)
│   ├── cert.pem / key.pem        # Self-signed cert (gitignored)
│   ├── classifier.onnx           # Trained CNN model (gitignored, optional)
│   │
│   ├── app/                      # Application source
│   │   ├── __init__.py           # Empty
│   │   ├── main.py               # FastAPI server: all endpoints (~370 lines)
│   │   ├── database.py           # SQLite: init, queries, hash chain (~175 lines)
│   │   ├── models.py             # Pydantic models (request/response) (~95 lines)
│   │   ├── tools_helpers.py      # Shared label generation for tests/tools
│   │   │
│   │   ├── crypto/               # CV layer
│   │   │   ├── __init__.py       # Empty
│   │   │   ├── anchor.py         # Anchor generation + comparison metrics (~170 lines)
│   │   │   └── preprocess.py     # QR detection + geometric anchor extraction (~170 lines)
│   │   │
│   │   └── ml/                   # AI / ML layer (optional, needs trained model)
│   │       ├── __init__.py       # Lazy-load ONNX model
│   │       ├── classifier.py     # predict_proba() inference wrapper
│   │       └── explainer.py      # Template-based AI Pharmacist (~360 lines)
│   │
│   ├── seed/
│   │   └── seed_data.py          # Seeds 3 batches (MM, VN, TH) with routes
│   │
│   ├── tests/                    # 35 tests total
│   │   ├── __init__.py           # Empty
│   │   ├── test_anchor.py        # 8 tests: CV generation + comparison + endpoint
│   │   ├── test_enhanced.py      # 4 tests: batch lookup, velocity, map data
│   │   ├── test_explain.py       # 3 tests: AI Pharmacist initial reply, follow-up, velocity
│   │   ├── test_https.py         # 2 tests: cert + HTTPS server
│   │   ├── test_partner_api.py   # 6 tests: register, list, idempotency, route replace
│   │   ├── test_preprocess.py    # 8 tests: QR detection, anchor extraction, blur levels
│   │   ├── test_samples.py       # 2 tests: pre-generated genuine + tampered PNGs
│   │   └── test_verify.py        # 2 tests: health endpoint + full HTTP roundtrip
│   │
│   └── tools/                    # CLI scripts
│       ├── benchmark.py          # 100-sample accuracy (hand-tuned CV + CNN if available)
│       ├── generate_cert.py      # Self-signed SSL cert (cryptography)
│       ├── generate_samples.py   # Creates genuine + tampered test PNGs
│       ├── onboard_partner.py    # Imports 5 realistic partner batches
│       ├── photo_robustness.py   # 13-condition phone photo simulation test
│       ├── printable_labels.py   # Creates sticker-ready demo label PNGs
│       ├── robustness_test.py    # 14-condition transformed 64x64 anchor test
│       ├── run_https.py          # Convenience HTTPS server wrapper
│       ├── TRAINING.md           # CNN training guide
│       └── train_classifier.py   # Self-contained CNN training script
│
├── web/                          # PWA (primary user interface)
│   ├── index.html                # Single-page app: input, verify, results, map, chat
│   ├── manifest.json             # PWA manifest for install-on-phone
│   └── sw.js                     # Service worker (caching, offline support)
│
├── mobile/                       # Expo React Native app (alternative, broken)
│   ├── App.tsx                   # Single-screen: camera → scan → result
│   ├── app.json                  # Expo config
│   ├── package.json
│   ├── tsconfig.json
│   └── assets/                   # Icons, splash screen
│
└── docs/
    ├── setup.md                  # Setup guide + HTTPS walkthrough
    ├── test.md                   # Testing guide with examples
    ├── architecture.md           # Full architecture document
    └── cnn-setup.md              # CNN training + deployment instructions
```

---

## 4. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Runtime** | Python ≥3.12 | Backend language |
| **Web server** | FastAPI + Uvicorn | Async HTTP server with auto-reload |
| **Database** | SQLite + aiosqlite | Zero-config, file-based. Tables: batches, route_points, scans |
| **Computer Vision** | OpenCV (opencv-python-headless) + NumPy | QR detection, image preprocessing, anchor comparison |
| **Image Processing** | Pillow (PIL) | Printable label generation with QR codes |
| **AI/ML** | ONNX Runtime (optional) | CNN inference on CPU. ~5ms per prediction |
| **ML Training** | PyTorch + torchvision (separate machine) | Train ResNet-18 on synthetic data |
| **QR Generation** | qrcode[pil] | Create QR codes on printable labels |
| **Frontend** | Vanilla JS + HTML + CSS (single file) | PWA, ~400 lines, no framework |
| **Map** | Leaflet.js + OpenStreetMap | Supply chain route visualization |
| **QR Scanning** | jsQR (browser) | Decode QR from camera video stream |
| **HTTPS Cert** | cryptography (Python) | Generate self-signed cert for development |
| **Testing** | pytest + pytest-asyncio + httpx | Backend tests with async HTTP client |
| **Mobile** | expo-camera + axios (Expo, optional) | Alternative React Native app |
| **Windows port issue** | Use port 8765 (Windows reserves 7997-8096 for Hyper-V) | |
| **Service** | Uvicorn | ASGI server, single-process |

---

## 5. API Endpoints

| Method | Path | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/health` | Health check | None |
| POST | `/api/v1/verify` | Main verification | None |
| GET | `/api/v1/chain/verify?serial=X` | Verify hash chain for serial | None |
| GET | `/api/v1/model/info` | Whether AI model is loaded | None |
| POST | `/api/v1/explain` | AI Pharmacist explanation | None |
| POST | `/api/v1/register` | Register a new batch | None (add in prod) |
| GET | `/api/v1/batches` | List all registered batches | None |
| GET | `/` | PWA web interface (static files) | None |

### 5.1 POST /api/v1/verify — Request

```json
{
  "batch_id": "BATCH-A",
  "serial": "001",
  "image_base64": "<base64 PNG, optional>",
  "lat": 16.8661,
  "lng": 96.1951,
  "timestamp": "2026-07-09T10:00:00"
}
```

### 5.2 POST /api/v1/verify — Response

```json
{
  "status": "verified",
  "confidence": 1.0,
  "message": "No anomalies detected. Product is authentic.",
  "metrics": {
    "degraded": false,
    "block_ncc": 0.999,
    "edge_ratio": 0.985,
    "hist_correlation": 0.892,
    "fft_correlation": 0.971,
    "bleed_ratio": 0.012,
    "edge_diff_ratio": 1.002,
    "preprocess": {"qr_found": true, ...}
  },
  "overlay_base64": null,
  "batch_info": {
    "batch_id": "BATCH-A",
    "region": "MYANMAR",
    "mint_date": "2026-06-01",
    "manufacturer": "PharmaCorp Myanmar Ltd.",
    "drug_name": "Paracetamol 500mg",
    "drug_use": "Fever & Pain Relief",
    "expiry": "2028-05",
    "route": [
      {"location_name": "PharmaCorp Factory — Yangon", "lat": 16.8661, "lng": 96.1951, "event": "Manufactured"},
      {"location_name": "Yangon International Port", ...},
      {"location_name": "Mandalay Distribution Hub", ...},
      {"location_name": "Mandalay Central Pharmacy", ...}
    ]
  },
  "scan_history": {
    "scan_count": 1,
    "velocity_alert": null,
    "density_alert": null,
    "gps_alert": null,
    "previous_scan": null,
    "chain_intact": true,
    "chain_message": "Chain intact — 1 records verified."
  },
  "ai_confidence": null
}
```

When the CNN is loaded, `ai_confidence` is:

```json
{
  "p_genuine": 0.998,
  "p_counterfeit": 0.002,
  "model": "resnet18",
  "model_agrees_with_cv": true
}
```

---

## 6. Crypto-Anchor CV (Detailed)

### 6.1 Anchor Format

The anchor is a deterministic 64×64 noise pattern:

```
16×16 grid of unique grayscale values (from SHA256 seed)
  ↓ kron with 4×4 ones block
64×64 image, each value repeated as a 4×4 block
```

**Why 4×4 blocks:** Pure 64×64 random noise has Nyquist at 32 cycles; even mild camera blur (σ=0.8 on a 600×400 label) attenuates it completely. With 16×16 unique values on 4×4 blocks, the highest frequency is 8 cycles — well below the blur cutoff.

### 6.2 Anchor Generation

```python
def generate_anchor(seed: str) -> np.ndarray:
    digest = sha256(seed.encode()).digest()
    rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
    grid = rng.integers(0, 256, (16, 16), dtype=np.uint8)
    return np.kron(grid, np.ones((4, 4), dtype=np.uint8))
```

Same seed always produces the same pattern. No images stored — just the seed `{batch_id}:{serial}`.

### 6.3 Comparison Metrics

| Metric | What it measures | Threshold | Genuine | Counterfeit |
|---|---|---|---|---|
| `block_ncc` | NCC of 16×16 downsampled grid | < 0.30 | High | Low (different seed) |
| `edge_ratio` | Sobel gradient at block boundaries / expected | < 0.70 | ~1.0 | < 0.7 (blurred blocks) |
| `hist_correlation` | 32-bin histogram match | (soft) | Variable | Variable |
| `fft_correlation` | Log-magnitude FFT NCC | (soft) | High | Lower |
| `bleed_ratio` | Fraction of pixels with diff > 30 | > 0.35 | Low | High |

**Degraded if:** `block_ncc < 0.30` OR (`edge_ratio < 0.70` AND (`bleed > 0.35` OR `hist < 0.20`)).

### 6.4 Simulating Photocopy

```python
def simulate_photocopy(anchor, severity=0.35):
    blur_k = max(3, int(severity * 9) | 1)  # odd kernel
    blurred = cv2.GaussianBlur(anchor, (blur_k, blur_k), 0)
    noise = random noise(severity)
    return blend(blurred, noise, severity * 0.5)
```

Used for generating test data and training the CNN.

### 6.5 Photo Preprocessing Pipeline

For phone photos (vs raw 64×64 PNG):

1. **QR Detection** with `cv2.QRCodeDetector` → 4 ordered corners (TL, TR, BR, BL)
2. **Sub-pixel offset** from QR detector TL to anchor TL, derived from template geometry:
   - Printed QR: 25 modules at 9.6px each = 240px total
   - Detector returns outer module corners, so effective width = 23 × 9.6 = 220.8px
   - Offset: anchor (30, 80) − detector_TL (339.6, 89.6) = (−309.6, −9.6)
3. **Geometric crop** at `detector_TL + offset × (qr_width_photo / 220.8)`
4. **NCC refinement**: 9×9 pixel search around predicted position to correct 1-2px QR jitter

If no QR found: returns `None`, endpoint falls back to `cv2.resize(gray, (64, 64))` (legacy top-left crop).

---

## 7. Spatial-Temporal Checks

### 7.1 Velocity (Haversine)

```
distance = haversine(prev_lat, prev_lng, curr_lat, curr_lng)  # in km
hours = (curr_timestamp - prev_timestamp)                      # in hours
speed = distance / hours                                        # in km/h

If speed > 120 km/h → velocity alert
```

### 7.2 Density

```
Count scans per serial in SQLite
If count + 1 > 3 → density alert (code replay)
```

### 7.3 GPS Region

Each batch has a region (MYANMAR, VIETNAM, THAILAND) with a bounding box:

```python
REGION_BOUNDS = {
    "MYANMAR": {min_lat: 10.0, max_lat: 28.5, min_lng: 92.0, max_lng: 101.0},
    "VIETNAM": {min_lat: 8.5, max_lat: 23.5, min_lng: 102.0, max_lng: 110.0},
    "THAILAND": {min_lat: 5.5, max_lat: 20.5, min_lng: 97.0, max_lng: 106.0},
}
```

If scan coordinates are outside the batch's region → GPS alert (diversion).

---

## 8. Hash Chain

Every scan record is cryptographically chained:

```
chain_hash = SHA256(serial | batch_id | lat | lng | timestamp | result | prev_hash)
```

- **First scan** for a serial: `prev_hash = "0" × 64`
- **Subsequent scans**: `prev_hash` = previous scan's `chain_hash`
- **Verification**: recompute all hashes from start, compare to stored values

Any modification to a past scan record breaks its hash, which breaks all subsequent hashes. The chain becomes irreparably broken.

**Why custom:** In pharma anti-counterfeit, the manufacturer IS the trusted authority. If they're malicious, no external blockchain prevents them. If they're honest, their own chain is as trustworthy as any distributed ledger — with zero infrastructure, zero gas, zero nodes.

---

## 9. AI Classifier (Optional)

### 9.1 Overview

| Property | Value |
|---|---|
| Task | Binary classification: genuine vs counterfeit |
| Input | 64×64 grayscale anchor crop |
| Output | `{p_genuine, p_counterfeit}` |
| Default arch | ResNet-18 (modified for 64×64 grayscale) |
| Params | ~11M |
| Inference time | ~5ms on CPU |
| Runtime | ONNX Runtime (no GPU needed) |
| Training data | Synthetic from `simulate_photocopy` + `random_augment` |

### 9.2 Training

```bash
# On GPU machine:
pip install torch torchvision numpy opencv-python-headless
python tools/train_classifier.py --epochs 20 --samples 50000
# Outputs: classifier.onnx (~45MB)
# Copy to backend/ on the laptop
```

The training script is **self-contained** — generates its own synthetic data, no backend dependencies needed.

### 9.3 Inference

```python
from app.ml.classifier import predict_proba, is_available

if is_available():
    proba = predict_proba(anchor_64x64)
    # {'p_genuine': 0.998, 'p_counterfeit': 0.002, 'model': 'resnet18'}
```

### 9.4 Override Logic

The CNN runs in parallel with the hand-tuned CV:

| CV says | CNN says | Threshold | Result |
|---|---|---|---|
| Genuine | Counterfeit | > 85% | Escalate to counterfeit |
| Counterfeit | Genuine | > 98% | Downgrade to verified |
| Agree | (any) | — | Use agreed verdict |

Missing `classifier.onnx` = no error, system runs on hand-tuned CV alone.

### 9.5 Current Model Status

The model trained with translation augmentation learned to classify ALL block-structured images as "genuine" — including tampered ones. The override threshold is at 98% p_genuine, which is rarely reached. **The model needs retraining with more aggressive photocopy simulation and more epochs to be useful.**

---

## 10. AI Pharmacist (Chatbot)

### 10.1 Architecture

Template-based explanation engine in `app/ml/explainer.py`. No LLM required — works offline, zero latency, no hallucination risk.

### 10.2 How it works

1. **Initial call** (empty user_message): generates a full explanation covering status, CV metrics, AI confidence, spatial-temporal checks, batch info, hash chain. Returns 3-5 suggested follow-ups.
2. **Follow-up call** (user selected a suggestion or typed a question): targets the specific topic (edge sharpness, pixel bleed, block NCC, AI model, velocity, density, GPS, hash chain, supply chain, hand-tuned vs AI).

### 10.3 Endpoint

```
POST /api/v1/explain
{
  "verify_response": { ... full verify result ... },
  "user_message": "What does edge sharpness mean?",
  "conversation": []  // optional, not used yet
}
→ { "reply": "...", "suggestions": ["..."] }
```

### 10.4 UI

Collapsible chat panel in `web/index.html`:
- Auto-opens after each verification
- Shows initial explanation as formatted markdown
- Clickable suggestion chips
- Free-text input for questions
- Toggleable (show/hide)

---

## 11. Database Schema

### 11.1 batches

| Column | Type | Description |
|---|---|---|
| `batch_id` | TEXT PK | e.g. "BATCH-A" |
| `region` | TEXT | Distribution region (MYANMAR, VIETNAM, THAILAND) |
| `mint_date` | TEXT | ISO date of manufacture |
| `manufacturer` | TEXT | (optional) Manufacturer name |
| `drug_name` | TEXT | (optional) Drug product name |
| `drug_use` | TEXT | (optional) Drug use description |
| `expiry` | TEXT | (optional) Expiry date |

### 11.2 route_points

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `batch_id` | TEXT FK | References batches |
| `point_order` | INTEGER | Sequence number (1 = origin) |
| `location_name` | TEXT | e.g. "Yangon Factory" |
| `lat`, `lng` | REAL | GPS coordinates |
| `event` | TEXT | e.g. "Manufactured", "Delivered to Pharmacy" |

### 11.3 scans

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `serial` | TEXT | Product serial number |
| `batch_id` | TEXT | Which batch it belongs to |
| `lat`, `lng` | REAL | GPS at time of scan |
| `timestamp` | TEXT | ISO timestamp |
| `result` | TEXT | "verified" / "flagged" / "counterfeit" |
| `scanned_at` | TEXT | Default `datetime('now')` |
| `chain_hash` | TEXT | SHA256 chain hash |

---

## 12. Seed Data

| Batch | Drug | Manufacturer | Region | Route |
|---|---|---|---|---|
| BATCH-A | Paracetamol 500mg | PharmaCorp Myanmar Ltd. | MYANMAR | Yangon → Port → Mandalay Hub → Mandalay Pharmacy |
| BATCH-B | Amoxicillin 250mg | VinPharm Joint Stock Co. | VIETNAM | Hanoi → Da Nang → HCMC → Saigon Pharmacy |
| BATCH-C | Omeprazole 20mg | SiamPharm Co., Ltd. | THAILAND | Bangkok → Chiang Mai → Phuket |

Plus 5 partner batches via `tools/onboard_partner.py`.

---

## 13. Test Results (Current Baseline)

### 13.1 Unit Tests (pytest)

**35 tests, all passing:**

| File | Tests | What it covers |
|---|---|---|
| `test_anchor.py` | 8 | Anchor gen, compare, verify endpoint |
| `test_enhanced.py` | 4 | Batch lookup, velocity, map data |
| `test_explain.py` | 3 | AI Pharmacist initial, follow-up, velocity |
| `test_https.py` | 2 | Cert file, HTTPS server |
| `test_partner_api.py` | 6 | Register, list, idempotency, route replacement |
| `test_preprocess.py` | 8 | QR detection, anchor extraction, blur levels |
| `test_samples.py` | 2 | Pre-generated genuine + tampered PNGs |
| `test_verify.py` | 2 | Health endpoint + HTTP roundtrip |

### 13.2 Benchmark (100 synthetic samples)

```
Hand-tuned CV:
  Accuracy:   100.0%  (50 TP, 50 TN, 0 FP, 0 FN)
CNC classifier:
  Accuracy:   100.0%  (same)
```

### 13.3 Robustness Test (14 transformed 64x64 anchors)

| Condition | Result | Confidence |
|---|---|---|
| Perfect match | ✅ verified | 100% |
| Camera blur (mild) | ✅ verified | 71% |
| Camera blur (moderate) | ❌ counterfeit | 39% |
| Camera blur (heavy) | ❌ counterfeit | 34% |
| Low light noise (mild) | ✅ verified | 98% |
| Low light noise (heavy) | ✅ verified | 93% |
| Resize 50% | ✅ verified | 100% |
| Resize 150% | ✅ verified | 83% |
| Rotation 5° | ❌ counterfeit | 27% |
| Rotation 15° | ❌ counterfeit | 50% |
| Photocopy mild | ✅ verified | 99% |
| Photocopy moderate | ✅ verified | 93% |
| Photocopy heavy | ✅ verified | 89% |
| Printer copy | ✅ verified | 87% |

**Genuine pass rate: 10/14 (71%)** — up from 5/14 baseline before block anchor redesign.

### 13.4 Photo Robustness (13 simulated phone photos)

| Condition | Result |
|---|---|
| Perfect scan | ✅ verified |
| Mild blur | ✅ verified |
| Moderate blur | ❌ counterfeit |
| Angled 5° | ❌ counterfeit |
| Angled 10° | ❌ counterfeit |
| Angled 15° | ❌ counterfeit |
| Low light | ❌ counterfeit |
| Bright light | ❌ counterfeit |
| Noisy low light | ❌ counterfeit |
| Heavy blur | ❌ counterfeit |
| Photocopy mild | ❌ counterfeit (correct) |
| Photocopy heavy | ❌ counterfeit (correct) |
| Photocopy + perspective | ❌ counterfeit (correct) |

**Genuine pass rate: 2/13 (15%).** The limitation is alignment — the geometric preprocessing pipeline has 1-2px error from QR detection jitter, which is catastrophic for pixel-exact NCC. The hand-tuned CV and CNN both see the same misaligned crop.

---

## 14. Areas for Improvement

### 14.1 CNN Model Training (Priority: High)

The current trained model is not discriminative enough — it classifies tampered images as genuine. Requires:
- More aggressive photocopy simulation in `random_augment` (higher severity, more noise variants)
- More training epochs (50+)
- Validation against real printed labels if possible
- See `docs/cnn-setup.md` and `tools/train_classifier.py`

### 14.2 Photo Alignment Robustness (Priority: Medium)

The 2/13 photo pass rate is the main bottleneck. Fixes:
- Expand the NCC search window (currently 9×9. Try 15×15)
- Template match at multiple rotations (check ±3°)
- Or: train the CNN with heavy shift augmentation (already done, but needs more)

### 14.3 Expo Mobile App (Priority: Low)

The mobile app is untested — it failed to run on the user's phone during initial setup. The PWA is the primary interface.

### 14.4 Production Readiness (Off-scope for competition)

- No authentication on API endpoints
- No rate limiting
- Self-signed cert only (no CA)
- SQLite single-file database (no replication)
- No logging / monitoring

---

## 15. How to Run

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

Or with HTTPS (for QR scanner camera):

```powershell
.venv\Scripts\python.exe tools/run_https.py
```

Then open `http://127.0.0.1:8765` (or `https://127.0.0.1:8765` for camera).

**Port note:** Windows reserves ports 7997-8096 for Hyper-V/WSL. Port 8000 won't bind. Always use 8765.

---

## 16. Quick Reference

| Task | Command |
|---|---|
| Run server | `.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload` |
| Run HTTPS | `.venv\Scripts\python.exe tools/run_https.py` |
| Generate cert | `.venv\Scripts\python.exe tools/generate_cert.py` |
| Run tests | `cd backend; .venv\Scripts\python.exe -m pytest -v` |
| Benchmark | `.venv\Scripts\python.exe tools/benchmark.py` |
| Robustness | `.venv\Scripts\python.exe tools/robustness_test.py` |
| Photo test | `.venv\Scripts\python.exe tools/photo_robustness.py` |
| Seed data | `.venv\Scripts\python.exe seed/seed_data.py` |
| Onboard partners | `.venv\Scripts\python.exe tools/onboard_partner.py` |
| Print labels | `.venv\Scripts\python.exe tools/printable_labels.py` |
| Train CNN | (on GPU machine) `python tools/train_classifier.py --epochs 20 --samples 20000` |
| Install deps | `uv pip install -e ".[dev]"` |
| Check ML model | `.venv\Scripts\python.exe -c "from app.ml.classifier import is_available; print(is_available())"` |
| Check API health | `curl http://127.0.0.1:8765/api/v1/health` |
