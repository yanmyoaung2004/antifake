# AntiFake — Architecture

## Overview

AntiFake is a two-layer anti-counterfeit verification system for the APICTA competition.

**Layer 1 — Spatial-Temporal (works today):** Detects suspicious scan behavior using batch/serial from any existing barcode. No factory cooperation needed. Three checks: velocity (impossible travel speed), density (replay attack), GPS (geographic diversion).

**Layer 2 — Crypto-Anchor CV (factory bonus):** Optional visual verification of a deterministic noise pattern printed on packaging. Uses OpenCV to detect microscopic print degradation from photocopying. Returns a heatmap overlay showing exactly where the counterfeit deviates.

**Stack:** Python/FastAPI + OpenCV + SQLite + Leaflet.js

---

## Tools & Libraries

| Layer | Tool | Purpose |
|---|---|---|
| Backend | FastAPI + Uvicorn | Async HTTP server, 3-check spatial-temporal engine |
| CV (optional) | OpenCV + NumPy | Edge, histogram, pixel bleed, heatmap overlay |
| Database | SQLite + aiosqlite | Batch registry, scan history, route points |
| Map | Leaflet.js + OpenStreetMap | Supply chain route with numbered markers |
| Mobile PWA | Service Worker + manifest.json | Installable on phone home screen |
| Camera (PWA) | file input + capture=environment | Phone camera via browser |
| QR | jsQR | Browser-based QR decoding from video stream |
| GPS | navigator.geolocation | Real phone location auto-detected |
| HTTP | httpx (Python), axios (mobile) | API communication |
| Testing | pytest, httpx | 16 unit + integration tests |
| Benchmark | tools/benchmark.py | 100 samples, 100% accuracy |
| Robustness | tools/robustness_test.py | 14 real-world condition tests |
| Labels | tools/printable_labels.py, qrcode | Printable demo stickers |

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
│   │   ├── main.py                      # FastAPI with POST /api/v1/verify + batch/velocity features
│   │   ├── database.py                  # SQLite queries (get_batch, get_route, get_scan_history, record_scan)
│   │   ├── models.py                    # Pydantic models (VerifyRequest, BatchInfo, ScanHistory, RoutePoint)
│   │   └── crypto/
│   │       └── anchor.py                # Core CV logic (all functions)
│   ├── seed/
│   │   └── seed_data.py                 # Seeds 3 batches with supply chain routes
│   ├── tests/
│   │   ├── test_anchor.py               # 8 tests for CV logic + API
│   │   ├── test_enhanced.py             # 4 tests for batch lookup + velocity + map data
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

## Database Schema (SQLite)

The database is auto-created on server startup. Re-run `seed/seed_data.py` to populate it.

### `batches` table

| Column | Type | Description |
|---|---|---|
| `batch_id` | TEXT PK | e.g. "BATCH-A" |
| `region` | TEXT | Distribution region, e.g. "MYANMAR" |
| `mint_date` | TEXT | ISO date of manufacture |

### `route_points` table

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `batch_id` | TEXT FK | References batches |
| `point_order` | INTEGER | Sequence number (1 = origin) |
| `location_name` | TEXT | e.g. "Yangon Factory" |
| `lat`, `lng` | REAL | GPS coordinates |
| `event` | TEXT | e.g. "Manufactured", "Delivered to Pharmacy" |

### `scans` table

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `serial` | TEXT | Product serial number |
| `batch_id` | TEXT | Which batch it belongs to |
| `lat`, `lng` | REAL | GPS at time of scan |
| `timestamp` | TEXT | ISO timestamp of scan |
| `result` | TEXT | "verified" or "counterfeit" |

---

## Verification Flow

The `POST /api/v1/verify` endpoint runs checks in sequence:

### Layer 1 — Spatial-Temporal (always runs)

1. **Velocity Check:** Computes Haversine distance between current and last scan GPS, divides by time delta. If speed > 120 km/h, returns velocity alert.
2. **Density Check:** Counts scans per serial via SQLite. If count > 2 (configurable), returns density alert for possible code replay.
3. **GPS Cross-Reference:** Compares scan location against batch distribution region polygon. If outside region, returns geographic diversion alert.

### Layer 2 — Crypto-Anchor CV (if image provided)

4. **Anchor Generation:** `SHA256(f"{batch_id}:{serial}")` → deterministic 64×64 noise pattern.
5. **Photo Extraction:** Decoded image is grayscaled and cropped to 64×64 anchor area.
6. **Comparison:** Three metrics against expected pattern:
   - Edge sharpness ratio (gradient comparison)
   - Histogram correlation (32-bin distribution match)
   - Pixel bleed ratio (pixels above 30-diff threshold)
7. **Heatmap:** If degraded, pixel-wise difference rendered as COLORMAP_JET overlay.

### Status Determination

- **counterfeit** — anchor check failed (CV layer)
- **flagged** — spatial-temporal alert triggered (velocity, density, or GPS)
- **verified** — all checks passed
- **error** — unexpected exception

```
distance = haversine(prev_lat, prev_lng, curr_lat, curr_lng)  ← in km
hours = (curr_timestamp - prev_timestamp)                      ← in hours
speed = distance / hours                                        ← in km/h
```

If `speed > 120 km/h` (configurable), a velocity alert is returned. Example:

> ⚠ Impossible movement detected — 570 km in 30 min (1140 km/h). Previous scan was at (16.9, 96.2).

---

## Journey Map

After verification, the web page renders an interactive Leaflet map showing:
1. **Route line** — green dashed line from factory to pharmacy
2. **Route markers** — numbered circles at each waypoint (blue = origin, yellow = transit, green = destination)
3. **Tooltips** — hover/tap to see location name and event
4. **Scan marker** — red dot at the current scan's GPS location

The map auto-zooms to fit all markers. The batch info section above the map shows the route as text: "Factory → Port → Distributor → Pharmacy".

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
| Scope | Full supply chain system | Anchor verification + batch tracing + velocity check |
| Infrastructure | Redis, Docker, Hardhat, blockchain | SQLite (zero-config) |
| Anomaly engine | Velocity, density, GPS with Redis | Velocity check via scan history in SQLite |
| Blockchain | Merkle root minting, scan events | Not included |
| Batch registry | Enterprise API | SQLite with seed data (3 batches, realistic routes) |
| Supply chain map | Not included | Leaflet.js interactive map with route waypoints |
| Offline support | AsyncStorage queue | Not included |
| Enterprise API | Batch creation with API key | Not included |
| Dependencies | 10+ services | Python + Node.js |
| Test count | 19 backend + 6 contracts | 16 backend |
| Setup time | ~1 hour | ~5 minutes |

---

## Testing

See [`test.md`](test.md) for full details.

```bash
cd version2/backend
uv run pytest -v          # 16 tests in under 3 seconds

# Test genuine (with batch info + velocity)
python -c "import httpx,base64;b64=base64.b64encode(open('sample_images/genuine_BATCH-A_001.png','rb').read()).decode();r=httpx.post('http://localhost:8000/api/v1/verify',json={'batch_id':'BATCH-A','serial':'001','image_base64':b64,'lat':16.8661,'lng':96.1951,'timestamp':'2026-07-06T10:00:00'});print(r.json().get('status'),'| batch:',r.json().get('batch_info',{}).get('batch_id'))"

# Test counterfeit
python -c "import httpx,base64;b64=base64.b64encode(open('sample_images/tampered_BATCH-A_001.png','rb').read()).decode();r=httpx.post('http://localhost:8000/api/v1/verify',json={'batch_id':'BATCH-A','serial':'001','image_base64':b64,'lat':16.8661,'lng':96.1951,'timestamp':'2026-07-06T10:00:00'});print(r.json().get('status'))"

# Velocity alert (scan same serial twice)
python -c "
import httpx,base64,sqlite3,os
con=sqlite3.connect('antifake.db');con.execute('DELETE FROM scans');con.commit();con.close()
b64=base64.b64encode(open('sample_images/genuine_BATCH-A_001.png','rb').read()).decode()
for lat,lng,ts in [(16.8661,96.1951,'2026-07-06T10:00:00'),(21.9731,96.0836,'2026-07-06T10:30:00')]:
    r=httpx.post('http://localhost:8000/api/v1/verify',json={'batch_id':'BATCH-A','serial':'V-TEST','image_base64':b64,'lat':lat,'lng':lng,'timestamp':ts})
    d=r.json();print('Scan',d['scan_history']['scan_count'],': alert' if d['scan_history'].get('velocity_alert') else ': ok')
"
```
