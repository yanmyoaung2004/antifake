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

# Start the server
uv run uvicorn app.main:app --reload
```

API available at `http://localhost:8000`.

Verify:

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok"}
```

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

> **Note:** If Expo Go fails to connect, use `npx expo start --tunnel` or test with curl/web instead.

---

## Web Interface (No Phone Required)

Open `http://localhost:8000` in any browser while the backend is running.

Drag & drop or tap to select a photo of the crypto-anchor. Click "Verify" to see the result. The page works on desktop and mobile browsers.

---

## Printable Demo Labels

```bash
cd version2\backend
uv run python tools/printable_labels.py
```

Output: `demo_labels/label_*.png` — print these on sticker paper and attach to medicine boxes for the physical demo.
