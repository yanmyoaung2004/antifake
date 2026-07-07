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

## Why SQLite + Hash Chain Instead of Blockchain

Every scan record is cryptographically chained using SHA256 — same concept as blockchain, zero infrastructure:

```python
chain_hash = SHA256(serial | batch_id | lat | lng | timestamp | result | prev_hash)
```

| | Blockchain | Our Hash Chain |
|---|---|---|
| Linking mechanism | Blocks with `prev_block_hash` | Scans with `prev_hash` |
| Tamper detection | Recompute + verify chain | Recompute + verify chain |
| Hash algorithm | SHA256 | SHA256 |
| Speed | ~12s per block | Instant |
| Cost | Gas fees | Zero |
| Infrastructure | Docker, nodes, wallets | One SQLite file |

**Why no blockchain:** In pharma anti-counterfeit, the manufacturer IS the trusted party. They made the medicine. If they're corrupt, no blockchain helps — they'd ship counterfeits from their own factory. If they're honest, their database is as trustworthy as any node. The hash chain gives cryptographic immutability (no record can be altered without detection) with zero operational overhead.

---

## Features

| Feature | Status |
|---|---|
| Velocity detection (Haversine) | Working |
| Density detection (replay alert) | Working |
| GPS cross-reference (region check) | Working |
| Crypto-anchor CV (optional bonus) | Working — 100% synthetic, tuned for real-world |
| Hash chain integrity (tamper-proof) | Working — SHA256 chained scan audit |
| Real browser GPS geolocation | Working — auto-detects phone location |
| Supply chain map (Leaflet.js) | Working — 3 seeded routes |
| PWA (install on phone) | Working — manifest + service worker |
| Demo labels (printable) | Working — genuine + counterfeit |
| QR scanning (jsQR) | Working — requires HTTPS for camera |
| Benchmark (100 samples) | 100% accuracy on synthetic images |
| Robustness test (14 conditions) | Documents real-world performance |

---

## Quick Start

```bash
cd backend
uv venv .venv --python 3.12
.venv\Scripts\activate
uv pip install -e ".[dev]"
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open http://localhost:8000. Type any batch ID + serial, tap **Verify**. No image needed.

---

## Testing

```bash
cd backend
.venv\Scripts\python.exe -m pytest -v          # 16 tests
.venv\Scripts\python.exe tools/benchmark.py    # 100 samples, 100% accuracy
.venv\Scripts\python.exe tools/robustness_test.py  # 14 real-world conditions
```

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI — velocity, density, GPS, optional CV
│   │   ├── database.py         # SQLite — batches, routes, scans
│   │   ├── models.py           # Pydantic models
│   │   └── crypto/anchor.py    # CV logic (generate, compare, heatmap)
│   ├── seed/seed_data.py       # 3 batches with supply chain routes
│   ├── tests/                  # 16 tests
│   ├── tools/
│   │   ├── benchmark.py        # 100% accuracy benchmark
│   │   ├── robustness_test.py  # 14-condition real-world test
│   │   ├── generate_samples.py # Test image generator
│   │   └── printable_labels.py # Demo sticker labels
│   ├── sample_images/          # 6 test images
│   └── demo_labels/            # 2 printable labels
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
