# AntiFake

A phone camera can tell the difference between a real medicine box and a counterfeit one.

AntiFake uses **crypto-anchor** technology — microscopic noise patterns embedded in packaging prints — to detect counterfeits that look identical to the human eye. After verification, it traces the product's supply chain journey from factory to pharmacy on an interactive map.

---

## How It Works

Every genuine medicine box gets a **Crypto-Anchor** at the factory — a unique random noise pattern printed next to the QR code. The pattern is deterministic: the backend regenerates it from the batch ID and serial number.

When a phone scans the QR and photographs the anchor area, the backend compares the photo against the expected pattern:

- **Edge sharpness** — real prints have crisp noise boundaries, photocopies blur them
- **Histogram correlation** — the noise distribution must match the original
- **Pixel bleed ratio** — counterfeit copies show smeared edges beyond the threshold

If any metric fails, the box is flagged as counterfeit and a **heatmap overlay** highlights exactly where the print deviated.

---

## Features

| Feature | What It Does |
|---|---|
| **Crypto-Anchor Verification** | Detects counterfeit prints by analyzing microscopic noise patterns with OpenCV |
| **Supply Chain Tracing** | Shows the product's route from factory to pharmacy on a Leaflet interactive map |
| **Velocity Alerts** | Detects cloned serials scanned from distant locations in impossible timeframes (Haversine formula) |
| **Batch Registry** | Stores batch metadata and route waypoints in SQLite |
| **Web Interface** | Drag-and-drop image upload with GPS input, works on desktop and mobile browsers |
| **Mobile App** | Expo app for QR scanning + camera capture |
| **Printable Demo Labels** | Generate sticker-ready labels with embedded crypto-anchors for physical demos |

---

## Quick Start

```bash
# Prerequisites: Python 3.12+, uv installed

cd backend
uv venv .venv --python 3.12
.venv\Scripts\activate
uv pip install -e ".[dev]"
uv run python seed/seed_data.py
uv run uvicorn app.main:app --reload
```

Open http://localhost:8000 in your browser. Upload a photo or drag a sample image from `backend/sample_images/`. Click **Verify**.

---

## Testing

```bash
cd backend
uv run pytest -v
# 16 tests pass in ~2 seconds
```

| Test Group | Count | What It Verifies |
|---|---|---|
| Core CV | 8 | Deterministic anchors, comparison metrics, API roundtrip |
| Enhanced | 4 | Batch lookup, velocity alerts, counterfeit + batch info |
| Samples | 2 | Pre-generated genuine/tampered images |
| API | 2 | Health endpoint, HTTP roundtrip |

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI — POST /api/v1/verify
│   │   ├── database.py        # SQLite — batches, routes, scans
│   │   ├── models.py          # Pydantic request/response models
│   │   └── crypto/anchor.py   # CV logic (generate, compare, heatmap)
│   ├── seed/seed_data.py      # Seeds 3 batches with supply chain routes
│   ├── tests/                 # 16 tests
│   ├── tools/                 # Label + sample generators
│   ├── sample_images/         # 6 pre-generated test images
│   └── demo_labels/           # 2 printable sticker labels
├── mobile/                    # Expo app (QR scan + camera)
├── web/index.html             # Drag-and-drop web interface
├── docs/
│   ├── setup.md               # Full setup instructions
│   ├── test.md                # Testing guide
│   └── architecture.md        # Architecture deep-dive
└── plan.md                    # Original build plan
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI + Uvicorn |
| Computer Vision | OpenCV + NumPy |
| Database | SQLite + aiosqlite |
| Map Visualization | Leaflet.js + OpenStreetMap |
| Mobile | React Native (Expo) |
| Web | Vanilla HTML, CSS, JavaScript |
| Testing | pytest + httpx |
| Linting | ruff |

---

## License

AntiFake v2 — APICTA 2026
