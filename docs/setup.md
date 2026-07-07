# AntiFake v2 — Setup

## Prerequisites

| Tool | Check |
|---|---|
| Python >= 3.12 | `python --version` |
| Node.js >= 20 | `node --version` |
| npm >= 10 | `npm --version` |

---

## Backend

```bash
cd version2\backend

# Create virtual environment
uv venv .venv --python 3.12
.venv\Scripts\activate

# Install dependencies
uv pip install -e ".[dev]"

# Seed the database with supply chain data
uv run python seed/seed_data.py

# Start the server
uv run uvicorn app.main:app --reload
```

The database (`antifake.db`) is created automatically on first startup if it doesn't exist. The seed script populates it with 3 batches (BATCH-A: Myanmar, BATCH-B: Vietnam, BATCH-C: Thailand) and their supply chain routes.

Verify:

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok"}
```

---

## Web Interface (Recommended — No Phone Required)

Open `http://localhost:8000` in any browser while the backend is running.

1. Tap or drag a photo of the crypto-anchor area
2. Optionally adjust the GPS coordinates (defaults to Yangon, Myanmar)
3. Click **Verify**
4. Result shows: authenticity badge, metrics, consumer medicine info, supply chain route on an interactive map, and velocity alerts if the same serial was scanned before

Phones can take a photo directly with the camera capture button. The page is a **PWA** — on Android, your browser will prompt to "Add to Home Screen" for a native-app-like experience. On iOS, tap Share → Add to Home Screen.

No personal data is collected or stored. Uploaded images are processed once and discarded.

---

## Mobile App (Expo)

```bash
cd version2\mobile

# Install dependencies
npm install
npx expo install expo-camera expo-barcode-scanner expo-network axios

# Start dev server
npx expo start
```

Scan the QR code with **Expo Go** on your phone.

> **Note:** If Expo Go fails to connect, use `npx expo start --tunnel` or test with the web interface instead.

---

## Printable Demo Labels

```bash
cd version2\backend
uv run python tools/printable_labels.py
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

Re-run `uv run python seed/seed_data.py` anytime to re-seed (skips existing batches).
