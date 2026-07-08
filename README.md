# AntiFake

A phone can detect counterfeit medicine without any special hardware — just a batch number and a camera.

AntiFake combines **spatial-temporal anomaly detection** (works with existing barcodes) with optional **crypto-anchor CV verification** (when factories collaborate). Track box movement, detect code replay, and optionally verify microscopic print patterns — all from a web browser.

---

## How It Works

### Without Crypto-Anchor (Works Today)

Every medicine box has a batch/lot number. Type it in and the system checks three things:

| Check | What It Detects |
|---|---|
| **Velocity** | Same serial scanned in two distant cities too quickly → cloned |
| **Density** | Same serial scanned too many times → code replay |
| **GPS** | Medicine scanned outside its distribution region → diversion |

No factory changes needed. Just a barcode or batch number.

### With Crypto-Anchor (Factory Bonus)

If pharmaceutical companies print a **deterministic noise pattern** on packaging, the system adds a fourth layer:
- **Edge sharpness** — real prints have crisp boundaries, photocopies blur them
- **Histogram correlation** — noise distribution must match the original
- **Pixel bleed** — counterfeit copies show smeared edges

A failing anchor check returns a **heatmap overlay** showing exactly where the print deviated.

---

## Custom Blockchain Implementation (Tamper-Proof Audit Trail)

AntiFake implements its own blockchain — not Ethereum, not Hardhat, not any existing platform. Every scan is a block, cryptographically chained to the previous one:

```
block_hash = SHA256(serial | batch_id | lat | lng | timestamp | result | prev_block_hash)
```

| | Traditional Blockchain | AntiFake Custom Blockchain |
|---|---|---|
| Block linking | `prev_block_hash` in each block | `prev_block_hash` in each scan |
| Consensus | Multiple nodes, PoW/PoS | Single source (manufacturer is trusted) |
| Tamper detection | Recompute + verify entire chain | Recompute + verify entire chain |
| Speed | ~12s per block | Instant |
| Cost | Gas fees per transaction | Zero |
| Infrastructure | Nodes, wallets, miners | One SQLite file + SHA256 |

**Why custom:** In pharmaceutical anti-counterfeit, the manufacturer IS the trusted authority. They made the medicine. If they were malicious, no external blockchain could prevent them from shipping counterfeits from their own factory. If they're honest, their own chain is as trustworthy as any distributed ledger. Our custom blockchain provides the same cryptographic immutability — no record can be altered without breaking all subsequent hashes — with zero infrastructure, zero gas, and zero nodes to manage.

---

## Features

| Feature | Status |
|---|---|
| Velocity detection (Haversine) | Working |
| Density detection (replay alert) | Working |
| GPS cross-reference (region check) | Working |
| Crypto-anchor CV (optional bonus) | Working — 16x16 block noise + edge sharpness metric |
| QR-based anchor localization | Working — detects printed QR, derives anchor position |
| Hash chain integrity (tamper-proof) | Working — SHA256 chained scan audit |
| Real browser GPS geolocation | Working — auto-detects phone location |
| HTTPS support (self-signed cert) | Working — `tools/generate_cert.py` + `run_https.py` |
| Supply chain map (Leaflet.js) | Working — 3 seeded + N partner routes |
| PWA (install on phone) | Working — manifest + service worker |
| Demo labels (printable) | Working — genuine + counterfeit |
| QR scanning (jsQR) | Working — requires HTTPS for camera |
| Partner onboarding API | Working — `POST /api/v1/register` + `GET /api/v1/batches` |
| Benchmark (100 samples) | 100% accuracy on synthetic images |
| Robustness test (14 conditions) | 10/14 genuine pass (vs 5/14 baseline) |
| Real-phone-photo test (13 scenarios) | Best-effort; spatial-temporal is the authoritative signal |

---

## Quick Start

```bash
cd backend
uv venv .venv --python 3.12
.venv\Scripts\activate
uv pip install -e ".[dev]"
.venv\Scripts\python.exe seed/seed_data.py
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open http://localhost:8000. Type any batch ID + serial, tap **Verify**. No image needed.

### With HTTPS (for camera/QR scanning on phone)

```bash
.venv\Scripts\python.exe tools/generate_cert.py   # one-time
.venv\Scripts\python.exe tools/run_https.py        # or: uvicorn with --ssl-keyfile/--ssl-certfile
```

See [docs/setup.md](docs/setup.md) for the full HTTPS walkthrough including iOS/Android cert trust.

---

## Partner Onboarding

Manufacturers and distributors can register batches via the API:

```bash
.venv\Scripts\python.exe tools/onboard_partner.py
```

Or call the endpoint directly:

```bash
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

`GET /api/v1/batches` returns all registered batches.

---

## Testing

```bash
cd backend
.venv\Scripts\python.exe -m pytest -v          # 32 tests
.venv\Scripts\python.exe tools/benchmark.py    # 100 samples, 100% accuracy
.venv\Scripts\python.exe tools/robustness_test.py  # 14 conditions
.venv\Scripts\python.exe tools/photo_robustness.py  # 13 simulated phone photos
```

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI — velocity, density, GPS, CV, partner API
│   │   ├── database.py         # SQLite — batches, routes, scans (with hash chain)
│   │   ├── models.py           # Pydantic models
│   │   ├── tools_helpers.py    # Shared label generation
│   │   └── crypto/
│   │       ├── anchor.py       # 16x16 block noise + comparison metrics
│   │       └── preprocess.py   # QR-based photo preprocessing pipeline
│   ├── seed/seed_data.py       # 3 baseline batches with full metadata
│   ├── tests/                  # 32 tests
│   ├── tools/
│   │   ├── benchmark.py        # 100% accuracy benchmark
│   │   ├── robustness_test.py  # 14-condition test
│   │   ├── photo_robustness.py # 13-condition phone photo test
│   │   ├── generate_samples.py # Test image generator
│   │   ├── printable_labels.py # Demo sticker labels
│   │   ├── generate_cert.py    # Self-signed cert for HTTPS
│   │   ├── run_https.py        # HTTPS server wrapper
│   │   └── onboard_partner.py  # Partner batch import demo
│   ├── sample_images/          # 6 test images
│   ├── demo_labels/            # 2 printable labels
│   ├── cert.pem, key.pem       # (gitignored, generated per-machine)
│   └── antifake.db             # (gitignored, auto-created)
├── web/index.html              # PWA web interface
├── mobile/                     # Expo app (alternative)
└── docs/                       # setup, test, architecture guides
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI |
| Computer Vision | OpenCV + NumPy |
| Database | SQLite + aiosqlite |
| Map | Leaflet.js + OpenStreetMap |
| PWA | Service Worker + manifest.json |
| QR | jsQR |
| Testing | pytest + httpx |
