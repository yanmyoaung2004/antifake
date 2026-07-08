# AntiFake v2 — Setup

## Prerequisites

| Tool | Check |
|---|---|
| Python >= 3.12 | `python --version` |
| Node.js >= 20 (only for Expo mobile, optional) | `node --version` |

---

## Quick Start (HTTP, local-only)

```bash
cd backend

# Create virtual environment
uv venv .venv --python 3.12
.venv\Scripts\activate

# Install dependencies
uv pip install -e ".[dev]"

# Seed the database with supply chain data
.venv\Scripts\python.exe seed/seed_data.py

# Start the server
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open `http://localhost:8000`. **HTTP works for everything except the camera/QR scanner** (which requires HTTPS).

---

## HTTPS (Required for Camera/QR Scanner)

Browsers block `getUserMedia` (camera access) on HTTP unless the page is on `localhost`. To scan QR codes with a phone camera, you need HTTPS.

### One-time setup

```bash
cd backend
.venv\Scripts\python.exe tools/generate_cert.py
```

This creates a self-signed `cert.pem` and `key.pem` (1-year validity) with SANs for `localhost`, `antifake.local`, `127.0.0.1`, and `0.0.0.0`.

### Run with HTTPS

```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem --reload
```

Or use the convenience script:

```bash
.venv\Scripts\python.exe tools/run_https.py
```

### Trust the cert on your phone

The browser will show a security warning because the cert is self-signed.

**iOS:**
1. Visit `https://<your-pc-ip>:8000` once
2. When the warning appears, download the cert profile (Settings > General > VPN & Device Management)
3. Trust it: **Settings > General > About > Certificate Trust Settings** — toggle ON for "AntiFake"

**Android:**
1. Visit `https://<your-pc-ip>:8000`
2. Tap "Advanced" → "Proceed anyway" (Chrome) or "Install certificate" (system installer)

**Find your PC's IP** (so the phone can reach the server):

```bash
# Windows
ipconfig

# macOS / Linux
ifconfig
# or
ip addr
```

Look for the IPv4 address on your WiFi/Ethernet adapter (e.g., `192.168.1.100`).

---

## Web Interface

The PWA at `http://localhost:8000` (or `https://...` for HTTPS) is the primary interface. From a phone on the same WiFi:

- **No image needed**: just enter batch/serial, tap Verify
- **Optional photo**: tap the camera area to take a photo of the crypto-anchor (requires HTTPS)
- **Auto GPS**: the page uses browser geolocation; the manual fallback works on any browser
- **QR scanner**: tap "Scan QR code" (requires HTTPS for camera)

Add to home screen for native-app experience:
- **Android**: Chrome menu → "Add to Home screen"
- **iOS**: Safari share button → "Add to Home Screen"

No personal data is collected or stored. Uploaded images are processed once and discarded.

---

## Mobile App (Expo, optional)

```bash
cd mobile
npm install
npx expo start
```

Scan the QR code with **Expo Go** on your phone.

> **Note:** If Expo Go fails to connect, use `npx expo start --tunnel` or test with the web interface instead. The PWA is the recommended path.

---

## Printable Demo Labels

```bash
cd backend
.venv\Scripts\python.exe tools/printable_labels.py
```

Output: `demo_labels/label_*.png` — print these on sticker paper and attach to medicine boxes for the physical demo.

---

## Supply Chain Data

The seed data includes realistic pharmaceutical supply chain routes:

| Batch | Region | Route |
|---|---|---|
| BATCH-A | Myanmar | Yangon Factory → Yangon Port → Mandalay Distributor → Mandalay Pharmacy |
| BATCH-B | Vietnam | Hanoi Factory → Da Nang Hub → Ho Chi Minh Distributor → Saigon Pharmacy |
| BATCH-C | Thailand | Bangkok Factory → Chiang Mai Distributor → Phuket Pharmacy |

Re-run `.venv\Scripts\python.exe seed/seed_data.py` anytime to re-seed (skips existing batches).
