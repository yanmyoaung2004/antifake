# AntiFake v2 — Setup Guide

## Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | >= 3.12 | `python --version` |
| pip | (included) | `python -m pip --version` |

---

## Step 1: Create Virtual Environment

```bash
cd backend

# Create virtual environment (using uv, or python -m venv)
uv venv .venv --python 3.12

# Activate it
.venv\Scripts\activate
```

---

## Step 2: Install Dependencies

```bash
uv pip install -e ".[dev]"
```

This installs:
- **Runtime:** FastAPI, Uvicorn, OpenCV, NumPy, Pillow, aiosqlite, qrcode, onnxruntime
- **Development:** pytest, pytest-asyncio, httpx, cryptography

---

## Step 3: Seed the Database

```bash
.venv\Scripts\python.exe seed/seed_data.py
```

Creates 3 batches with realistic supply chain routes:

| Batch | Drug | Manufacturer | Region | Route |
|---|---|---|---|---|
| BATCH-A | Paracetamol 500mg | PharmaCorp Myanmar | MYANMAR | Yangon → Port → Mandalay Hub → Pharmacy |
| BATCH-B | Amoxicillin 250mg | VinPharm | VIETNAM | Hanoi → Da Nang → HCMC → Pharmacy |
| BATCH-C | Omeprazole 20mg | SiamPharm | THAILAND | Bangkok → Chiang Mai → Phuket |

Re-run anytime to restore (skips existing batches).

---

## Step 4: Start the Server

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

Open **http://127.0.0.1:8765** in your browser.

> **Port note:** Windows reserves 7997–8096 for Hyper-V. If you see `WinError 10013`, use `8765` or another port above 10000.

---

## Step 5: Verify It Works

```powershell
# Open the web UI and type:
Batch ID: BATCH-A
Serial:   001

# Tap "Verify"
```

Expected result: green badge "AUTHENTIC", supply chain map with 4 markers, and the Verification Assistant chat panel auto-opens below.

### Test with curl:

```powershell
.venv\Scripts\python.exe -c "import httpx; r = httpx.post('http://127.0.0.1:8765/api/v1/verify', json={'batch_id':'BATCH-A','serial':'001','lat':16.8661,'lng':96.1951}); print(r.json()['status'], r.json()['message'])"
```

Expected output: `verified No anomalies detected. Product is authentic.`

---

## Using the System

### Without an Image (Recommended for Demo)

Type any batch ID + serial into the text fields and tap **Verify**. The system checks three things:

| Check | What it detects |
|---|---|
| **Velocity** | Same serial scanned in two cities too quickly → cloned |
| **Density** | Same serial scanned too many times → code replay |
| **GPS** | Medicine outside its distribution region → diversion |

### With an Image (Crypto-Anchor Bonus)

If the medicine box has a printed crypto-anchor (noise pattern), tap the camera area to upload a photo. The system adds two more checks:

| Check | What it detects |
|---|---|
| **Hand-tuned CV** | Edge sharpness, block NCC, histogram, FFT, pixel bleed |
| **CNN** (if model loaded) | ResNet-18 second opinion, overrides at 85%/98% thresholds |

A failing anchor check shows a **heatmap overlay** highlighting where the print deviated.

### QR Scanner (Requires HTTPS)

Tap "Scan QR code" to use the phone camera. The QR encodes `batch_id|serial`. Requires HTTPS for camera access (see HTTPS section below).

### Verification Assistant

After any verification, the chat panel auto-opens with a full explanation. Tap suggestion chips or ask your own questions:

- "What does edge sharpness mean?"
- "How does the hash chain work?"
- "What triggered the velocity alert?"
- "Where did this batch come from?"

---

## HTTPS (For Camera / QR Scanner on Phone)

Browsers block camera access on HTTP (except localhost). To scan QR codes from a phone:

### One-time cert generation

```bash
cd backend
.venv\Scripts\python.exe tools/generate_cert.py
```

Creates `cert.pem` + `key.pem` (1-year, self-signed).

### Start with HTTPS

```bash
.venv\Scripts\python.exe tools/run_https.py
```

Or manually:

```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8765 --ssl-keyfile key.pem --ssl-certfile cert.pem --reload
```

### Trust the cert on your phone

Find your PC's local IP:

```bash
# Windows
ipconfig | findstr IPv4

# macOS / Linux
ifconfig
```

**iOS:**
1. Visit `https://<your-pc-ip>:8765`
2. Download the cert profile (Settings > General > VPN & Device Management)
3. Trust it: **Settings > General > About > Certificate Trust Settings** — toggle ON for "AntiFake"

**Android:**
1. Visit `https://<your-pc-ip>:8765`
2. Tap "Advanced" → "Proceed anyway"

---

## Optional: Deploy the CNN Classifier

If you have `classifier.onnx` (trained on a GPU machine), place it in the `backend/` folder:

```bash
# Copy the trained model
cp /path/to/classifier.onnx backend/

# Restart the server — it auto-detects the model
```

Verify it's loaded:

```bash
curl http://127.0.0.1:8765/api/v1/model/info
```

Expected:

```json
{"ml_available": true, "model_path": "backend/classifier.onnx", "load_error": null}
```

The CNN runs alongside the hand-tuned CV on every verify request. The response includes `ai_confidence`:

```json
{
  "ai_confidence": {
    "p_genuine": 0.998,
    "p_counterfeit": 0.002,
    "model": "resnet18",
    "model_agrees_with_cv": true
  }
}
```

---

## Onboarding Partners

Import realistic partner batches:

```bash
.venv\Scripts\python.exe tools/onboard_partner.py
```

Registers 5 batches across Myanmar, Vietnam, and Thailand. To register a single batch via API:

```bash
curl -X POST http://127.0.0.1:8765/api/v1/register \
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

List all registered batches:

```bash
curl http://127.0.0.1:8765/api/v1/batches
```

---

## Printable Demo Labels

Generate sticker-ready labels for the physical demo:

```bash
.venv\Scripts\python.exe tools/printable_labels.py
```

Output: `demo_labels/label_*.png`. Print on sticker paper and attach to medicine boxes. One label verifies as genuine, the other as counterfeit.

---

## Running Tests

```powershell
# Unit tests (35 total)
.venv\Scripts\python.exe -m pytest -v

# Accuracy benchmark (100 synthetic samples)
.venv\Scripts\python.exe tools/benchmark.py

# Robustness test (14 transformed anchors)
.venv\Scripts\python.exe tools/robustness_test.py

# Phone photo simulation (13 scenarios)
.venv\Scripts\python.exe tools/photo_robustness.py
```

---

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/verify` | Main verification |
| POST | `/api/v1/assist` | Verification Assistant chat |
| GET | `/api/v1/model/info` | CNN model availability |
| GET | `/api/v1/chain/verify?serial=X` | Hash chain integrity |
| POST | `/api/v1/register` | Register a new batch |
| GET | `/api/v1/batches` | List all batches |

---

## Quick Reference

```powershell
# Start server (HTTP)
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload

# Start server (HTTPS)
.venv\Scripts\python.exe tools/run_https.py

# Run tests
.venv\Scripts\python.exe -m pytest -v

# Seed data
.venv\Scripts\python.exe seed/seed_data.py

# Onboard partners
.venv\Scripts\python.exe tools/onboard_partner.py

# Print labels
.venv\Scripts\python.exe tools/printable_labels.py

# Generate cert
.venv\Scripts\python.exe tools/generate_cert.py

# Benchmark
.venv\Scripts\python.exe tools/benchmark.py
```
