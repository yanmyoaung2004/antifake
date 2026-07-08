# AntiFake — Architecture

## Overview

AntiFake is a two-layer anti-counterfeit verification system for the APICTA competition.

**Layer 1 — Spatial-Temporal (works today):** Detects suspicious scan behavior using batch/serial from any existing barcode. No factory cooperation needed. Three checks: velocity (impossible travel speed), density (replay attack), GPS (geographic diversion).

**Layer 2 — Crypto-Anchor CV (factory bonus):** Optional visual verification of a deterministic noise pattern printed on packaging. Detects microscopic print degradation from photocopying. The anchor is a 16×16 grid of unique grayscale values, each rendered as a 4×4 block (so the printed anchor is 64×64 total). This coarse structure survives mild camera blur but is destroyed by photocopying.

**Custom Hash Chain:** Every scan is cryptographically chained to the previous via SHA256. Tampering with any record breaks the chain. No nodes, no gas, no infrastructure — just SQLite + SHA256.

**Stack:** Python/FastAPI + OpenCV + SQLite + Leaflet.js + PWA

---

## Two-Layer Design

```
                      ┌──────────────────────────────┐
                      │   Phone (browser / PWA)      │
                      │  - Manual batch/serial entry │
                      │  - QR scan (HTTPS only)      │
                      │  - Optional photo upload     │
                      │  - Browser geolocation       │
                      └──────────┬───────────────────┘
                                 │  HTTPS POST /api/v1/verify
                                 │  {batch_id, serial, image_base64?,
                                 │   lat, lng, timestamp}
                                 ▼
                ┌────────────────────────────────────────┐
                │  FastAPI (app/main.py)                 │
                │                                        │
                │  1. CV layer (if image provided)       │
                │     ├─ preprocess_photo()              │
                │     │   ├─ detect QR                    │
                │     │   ├─ derive anchor position       │
                │     │   └─ crop 64x64                  │
                │     └─ compare_anchors()               │
                │         ├─ block NCC                   │
                │         ├─ edge sharpness ratio        │
                │         ├─ histogram correlation       │
                │         ├─ FFT correlation             │
                │         └─ bleed ratio                 │
                │                                        │
                │  2. Spatial-temporal layer (always)    │
                │     ├─ velocity (Haversine)            │
                │     ├─ density (replay count)          │
                │     └─ GPS region check                │
                │                                        │
                │  3. Hash chain                         │
                │     └─ record_scan() appends SHA256    │
                │        to chain                        │
                │                                        │
                │  4. Status determination               │
                │     ├─ counterfeit (CV fail)           │
                │     ├─ flagged (spatial alert)         │
                │     └─ verified (all pass)             │
                └──────────┬─────────────────────────────┘
                           │
                           ▼
                ┌──────────────────────────┐
                │  SQLite (antifake.db)    │
                │  - batches               │
                │  - route_points          │
                │  - scans (with chain)    │
                └──────────────────────────┘
```

The two layers are independent: the CV layer is best-effort and degrades gracefully on real phone photos. The spatial-temporal + hash chain layer is authoritative and works with just batch/serial (no image required).

---

## Tools & Libraries

| Layer | Tool | Purpose |
|---|---|---|
| Backend | FastAPI + Uvicorn | Async HTTP server |
| CV | OpenCV + NumPy | Anchor generation, comparison, heatmap, QR detection |
| Preprocessing | cv2.QRCodeDetector | Detect printed QR for anchor localization |
| Database | SQLite + aiosqlite | Batches, routes, scans (with hash chain) |
| Map | Leaflet.js + OpenStreetMap | Supply chain route with numbered markers |
| PWA | Service Worker + manifest.json | Installable on phone home screen |
| Camera (PWA) | file input + capture=environment | Phone camera via browser |
| QR (PWA) | jsQR | Browser-based QR decoding (requires HTTPS) |
| GPS | navigator.geolocation | Real phone location auto-detected |
| HTTP | httpx | API client + tests |
| Cert | cryptography | Self-signed cert generation for HTTPS |
| Testing | pytest + httpx | 32 unit + integration tests |
| Benchmark | tools/benchmark.py | 100 samples, 100% accuracy |
| Robustness | tools/robustness_test.py | 14 conditions on transformed anchors |
| Photo | tools/photo_robustness.py | 13 simulated phone photo scenarios |
| Labels | tools/printable_labels.py, qrcode | Printable demo stickers |
| HTTPS | tools/generate_cert.py, run_https.py | Self-signed cert + HTTPS server wrapper |
| Partner | tools/onboard_partner.py | Realistic batch import demo |

---

## Directory Structure

```
antifake/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI: verify, chain, register, batches
│   │   ├── database.py              # SQLite: get_batch, get_route, record_scan,
│   │   │                            #   verify_chain, upsert_batch, add_route_point
│   │   ├── models.py                # Pydantic models (verify, register, list, etc.)
│   │   ├── tools_helpers.py         # Shared label generation (printable_labels)
│   │   └── crypto/
│   │       ├── anchor.py            # 16x16 block noise + comparison metrics
│   │       └── preprocess.py        # QR detection + anchor extraction
│   ├── seed/
│   │   └── seed_data.py             # 3 baseline batches with full metadata
│   ├── tests/                       # 32 tests
│   │   ├── test_anchor.py           # 8 tests: CV logic + endpoint
│   │   ├── test_enhanced.py         # 4 tests: batch + velocity + map
│   │   ├── test_https.py            # 2 tests: cert + HTTPS server
│   │   ├── test_partner_api.py      # 6 tests: register, list, idempotency
│   │   ├── test_preprocess.py       # 8 tests: QR detection, photo pipeline
│   │   ├── test_samples.py          # 2 tests: pre-generated images
│   │   └── test_verify.py           # 2 tests: health + roundtrip
│   ├── tools/
│   │   ├── benchmark.py             # 100 samples, 100% accuracy
│   │   ├── generate_cert.py         # Self-signed cert generator
│   │   ├── generate_samples.py      # Test PNG generator
│   │   ├── onboard_partner.py       # Realistic partner batch import
│   │   ├── photo_robustness.py      # 13-condition phone photo test
│   │   ├── printable_labels.py      # Demo sticker labels
│   │   ├── robustness_test.py       # 14-condition transformed anchor test
│   │   └── run_https.py             # HTTPS server wrapper
│   ├── sample_images/               # 6 pre-generated test images
│   ├── demo_labels/                 # 2 printable label PNGs
│   ├── cert.pem, key.pem            # Self-signed cert (gitignored, generated)
│   ├── antifake.db                  # SQLite (gitignored, auto-created)
│   └── pyproject.toml
├── web/
│   ├── index.html                   # PWA web interface (single file, ~400 lines)
│   ├── manifest.json                # PWA manifest
│   └── sw.js                        # Service worker
├── mobile/                          # Expo app (alternative, optional)
│   ├── App.tsx
│   ├── app.json
│   └── package.json
└── docs/
    ├── setup.md                     # Setup + HTTPS + cert trust
    ├── test.md                      # Testing guide (32 tests)
    └── architecture.md              # This file
```

---

## Data Flow: Verify

```
Phone                              Backend
  │                                  │
  │  batch_id, serial,               │
  │  image_base64?,                   │
  │  lat, lng, timestamp              │
  │ ────────────────────────────────>│
  │                                  │
  │                                  │  seed = f"{batch_id}:{serial}"
  │                                  │  expected = generate_anchor(seed)
  │                                  │      → 16x16 grid → 64x64 kron
  │                                  │
  │                                  │  if image:
  │                                  │    actual, info = preprocess_photo(
  │                                  │        img, expected)
  │                                  │    ├─ detect_qr_corners
  │                                  │    ├─ crop 64x64 at predicted position
  │                                  │    └─ 9x9 NCC refinement
  │                                  │    metrics = compare_anchors(...)
  │                                  │      ├─ block NCC (16x16 downsampled)
  │                                  │      ├─ edge sharpness ratio
  │                                  │      ├─ histogram correlation
  │                                  │      ├─ FFT correlation
  │                                  │      └─ bleed ratio
  │                                  │
  │                                  │  # spatial-temporal (always)
  │                                  │  history = get_scan_history(serial)
  │                                  │  velocity = haversine(prev, curr) / hours
  │                                  │  density = scan_count + 1 > threshold
  │                                  │  gps = batch_region.contains(scan_lat, scan_lng)
  │                                  │
  │                                  │  # hash chain
  │                                  │  prev_hash = last(chain for this serial)
  │                                  │  chain_hash = sha256(serial|batch|lat|lng|
  │                                  │                     timestamp|result|prev_hash)
  │                                  │  INSERT INTO scans (..., chain_hash)
  │                                  │
  │  {status, confidence, message,   │
  │   metrics, overlay_base64?,       │
  │   batch_info, scan_history}      │
  │ <────────────────────────────────│
```

---

## Core CV Logic

### Anchor Format

The crypto-anchor is a deterministic 64×64 noise pattern with structure:

```
16x16 grid of unique grayscale values
  ↓ kron with 4x4 ones
64x64 image, each value rendered as 4x4 block
```

Why 16x16 on 4x4 blocks (not pure 64x64 noise):
- Pure 64x64 noise has Nyquist at 32 cycles. Mild camera blur (σ=0.8 in 600x400 label) attenuates that completely.
- 16x16 unique values on 4x4 blocks: highest "frequency" is 8 cycles across the anchor, well below the blur cutoff. Survives mild blur, destroyed by photocopying.

```python
def generate_anchor(seed: str) -> np.ndarray:
    digest = sha256(seed.encode()).digest()
    rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
    grid = rng.integers(0, 256, (16, 16), dtype=np.uint8)
    return np.kron(grid, np.ones((4, 4), dtype=np.uint8))
```

The same seed always produces the exact same pattern. The backend regenerates the expected pattern for any serial without storing images.

### Comparison Metrics

| Metric | What it measures | Genuine | Photocopy |
|---|---|---|---|
| `block_ncc` | 16x16 downsampled NCC | High (0.9+) | High (block averages preserved) |
| `edge_ratio` | Sobel gradient at block boundaries / expected | ~1.0 (sharp) | <0.7 (blurred) |
| `hist_correlation` | 32-bin histogram match | Variable (random) | Variable |
| `fft_correlation` | Log-magnitude FFT NCC | High | Lower |
| `bleed_ratio` | Fraction of pixels with diff > 30 | Low | High |

A sample is **degraded** (counterfeit) if:
- `block_ncc < 0.30` (different seed or heavy damage), OR
- `edge_ratio < 0.70` AND (`bleed > 0.35` OR `hist < 0.20`) (photocopy signature)

Confidence is a weighted blend of normalized metrics.

### Photo Preprocessing Pipeline

For real phone photos (vs raw 64x64 PNG), the pipeline is:

1. **QR detection** with `cv2.QRCodeDetector` → 4 ordered corners
2. **Sub-pixel offset** from the QR's TL to the anchor's TL, computed from the template geometry (printed QR at 25 modules, 9.6 px each, with the detector returning outer module corners)
3. **Geometric crop** at the predicted position, scaled by `photo_qr_width / 220.8` (detector's effective QR width in template)
4. **9×9 NCC refinement** when the expected pattern is available (corrects the 1-2 px jitter of QR detection)

If no QR is detected, the system returns `actual = None` and the verify endpoint falls back to `cv2.resize(gray, (64, 64))` (legacy top-left crop).

---

## API

### `POST /api/v1/verify`

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

Response fields:

| Field | Description |
|---|---|
| `status` | `verified` / `flagged` / `counterfeit` / `error` |
| `confidence` | 0.0–1.0 from CV metrics |
| `message` | Human-readable explanation |
| `metrics` | Block NCC, edge ratio, hist, FFT, bleed (when image provided) |
| `overlay_base64` | Heatmap PNG (only when counterfeit) |
| `batch_info` | Manufacturer, drug, region, mint_date, expiry, route (if registered) |
| `scan_history` | scan_count, velocity_alert, density_alert, gps_alert, chain_intact |

### `POST /api/v1/register`

Idempotent batch registration for partner onboarding:

```json
{
  "batch_id": "MM-PARA-2026-07",
  "region": "MYANMAR",
  "mint_date": "2026-07-01",
  "manufacturer": "PharmaCorp Myanmar Ltd.",
  "drug_name": "Paracetamol 500mg",
  "drug_use": "Fever & Pain Relief",
  "expiry": "2028-06",
  "route": [
    {"location_name": "Factory", "lat": 16.8661, "lng": 96.1951, "event": "Manufactured"},
    {"location_name": "Pharmacy", "lat": 21.9588, "lng": 96.0896, "event": "Delivered"}
  ]
}
```

Returns `{batch_id, inserted, message}`. Re-registering an existing batch updates metadata and replaces the route.

### `GET /api/v1/batches`

Returns all registered batches with full metadata. Used by partner dashboards.

### `GET /api/v1/chain/verify?serial=X`

Returns the integrity status of the hash chain for a given serial. UI shows a green 🔗 badge if intact, red 🔓 if tampered.

### `GET /api/v1/health`

Returns `{"status": "ok"}`.

---

## Database Schema (SQLite)

The database is auto-created on server startup. Re-run `seed/seed_data.py` to populate.

### `batches` table

| Column | Type | Description |
|---|---|---|
| `batch_id` | TEXT PK | e.g. "BATCH-A" |
| `region` | TEXT | Distribution region (MYANMAR, VIETNAM, THAILAND) |
| `mint_date` | TEXT | ISO date of manufacture |
| `manufacturer` | TEXT | (optional) |
| `drug_name` | TEXT | (optional) |
| `drug_use` | TEXT | (optional) |
| `expiry` | TEXT | (optional) |

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
| `timestamp` | TEXT | ISO timestamp |
| `result` | TEXT | "verified" / "flagged" / "counterfeit" |
| `scanned_at` | TEXT | Default `datetime('now')` |
| `chain_hash` | TEXT | SHA256 chain hash (see below) |

---

## Hash Chain Integrity

Every scan record is cryptographically chained using SHA256:

```
chain_hash = SHA256(serial | batch_id | lat | lng | timestamp | result | prev_hash)
```

- First scan: `prev_hash = "0" * 64`
- Subsequent scans: `prev_hash` = `chain_hash` of the previous scan for that serial
- Verification: recompute every hash from start to end, compare with stored values

If any record is modified, its hash changes, breaking all subsequent hashes. The chain becomes irreparably broken — instantly detectable via `GET /api/v1/chain/verify?serial=X`.

This provides blockchain-level immutability with zero infrastructure — no nodes, no gas, no network. The web UI shows a green 🔗 badge for intact chains and a red 🔓 badge if the chain is broken.

---

## Spatial-Temporal Checks

### Velocity (Haversine)

```
distance = haversine(prev_lat, prev_lng, curr_lat, curr_lng)  // in km
hours = (curr_timestamp - prev_timestamp)                       // in hours
speed = distance / hours                                        // in km/h
```

If `speed > 120 km/h`, returns a velocity alert. Example:

> ⚠ Impossible movement detected — 570 km in 30 min (1140 km/h). Previous scan was at (16.9, 96.2).

### Density (Replay)

Counts scans per serial. If `count + 1 > 2` (configurable), returns a density alert.

### GPS Region

Each batch has a distribution region (MYANMAR, VIETNAM, THAILAND). If the scan's coordinates fall outside the region's bounding box, returns a GPS alert.

---

## Status Determination

| Status | Condition |
|---|---|
| `counterfeit` | CV layer failed (block NCC < 0.3 or photocopy signature) |
| `flagged` | Spatial-temporal alert (velocity, density, or GPS) but CV passed |
| `verified` | All checks passed |
| `error` | Unexpected exception |

---

## Journey Map

The web page renders an interactive Leaflet map showing:
1. **Route line** — green dashed line from factory to pharmacy
2. **Route markers** — numbered circles (blue = origin, yellow = transit, green = destination)
3. **Tooltips** — hover/tap for location name and event
4. **Scan marker** — red dot at the current scan's GPS

Map auto-zooms to fit all markers.

---

## HTTPS for Camera Access

Browsers block `getUserMedia` (camera) on HTTP unless on `localhost`. The QR scanner requires HTTPS on a phone.

**One-time setup:**
```bash
.venv\Scripts\python.exe tools/generate_cert.py
```

**Run with HTTPS:**
```bash
.venv\Scripts\python.exe tools/run_https.py
# or
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  --ssl-keyfile key.pem --ssl-certfile cert.pem
```

**Trust the cert on phone:**
- iOS: Settings > General > About > Certificate Trust Settings
- Android: Chrome > Site settings > secure connection

See [setup.md](setup.md) for the full walkthrough.

---

## Demo Labels

`tools/printable_labels.py` generates 600×400 PNGs ready for sticker paper:

```
┌──────────────────────────────────────┐
│ Batch: BATCH-A  Serial: 001         │
│                                      │
│  ┌──────────┐    ┌──────────┐       │
│  │ Crypto   │    │   QR     │       │
│  │ Anchor   │    │  Code    │       │
│  │ (64×64)  │    │ (240×240)│       │
│  │ 16x16 on │    │ 25-mod   │       │
│  │ 4x4 blk  │    │          │       │
│  └──────────┘    └──────────┘       │
│                                      │
│  LAYER 2          LAYER 1            │
│  Crypto Anchor    QR Code            │
│                                      │
│          GENUINE or COUNTERFEIT      │
└──────────────────────────────────────┘
```

Print both labels, stick on two identical boxes. The genuine label verifies; the counterfeit label (with photocopy simulation) flags.

---

## Partner Onboarding

Manufacturers and distributors can register batches via the API:

```bash
.venv\Scripts\python.exe tools/onboard_partner.py
```

Imports 5 representative partner batches with realistic drug names, manufacturers, and geographically accurate supply chain points (Myanmar, Vietnam, Thailand).

In production, the manufacturer's ERP would call `POST /api/v1/register` directly to register each batch as it's produced.

---

## Testing

See [test.md](test.md) for the full guide.

- **32 unit + integration tests** (`pytest -v`)
- **100-sample benchmark** (100% accuracy on synthetic anchors)
- **14-condition robustness** on transformed 64x64 anchors
- **13-condition photo robustness** on simulated phone photos
