# AntiFake — Setup Guide

## Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | >= 3.12 | `python --version` |
| Node.js | >= 20 | `node --version` |
| npm | >= 10 | `npm --version` |
| Docker + Compose | latest | `docker compose version` |
| Git | any | `git --version` |

---

## Dependency Services

Redis and the local EVM chain (Hardhat/anvil) run in Docker. You start them before the backend and keep them running.

```bash
docker compose up -d redis hardhat
```

This starts:
- **Redis** on `localhost:6379`
- **Hardhat (anvil)** on `localhost:8545`

Verify:
```bash
docker compose ps
# NAME              STATUS          PORTS
# antifake-redis-1   Up             0.0.0.0:6379->6379/tcp
# antifake-hardhat-1 Up             0.0.0.0:8545->8545/tcp
```

Stop them when done:
```bash
docker compose stop redis hardhat
```

---

## 1. Backend

### 1.1 Virtual Environment

```bash
cd backend

# Using uv (recommended — fast)
uv venv .venv --python 3.12
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # Mac/Linux
```

### 1.2 Install Dependencies

```bash
uv pip install -e ".[dev]"
```

Installs: `fastapi`, `uvicorn`, `redis`, `fakeredis`, `web3`, `pillow`, `opencv-python-headless`, `numpy`, `qrcode`, `pytest`, `httpx`, `ruff`, `mypy`.

### 1.3 Run

Make sure Docker services are running first (see above), then:

```bash
uv run uvicorn app.main:app --reload
# API at http://localhost:8000
```

### 1.4 Verify

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok","redis":true,"rpc":true}
```

### 1.5 Run Tests

Tests use `fakeredis` — no Docker needed.

```bash
uv run pytest . --cov -v
# 19 tests, 86%+ coverage
```

### 1.6 Lint + Type Check

```bash
uv run ruff check .
uv run mypy .
```

---

## 2. Smart Contracts

### 2.1 Install Dependencies

```bash
cd contracts
npm install
```

### 2.2 Compile

```bash
npx hardhat compile
```

### 2.3 Test

```bash
npx hardhat test
# 6 tests pass
```

### 2.4 Deploy to Local Chain

The Hardhat node is already running in Docker (started above).

```bash
npx hardhat run scripts/deploy.js --network localhost
# Save the printed contract address — you'll need it for CONTRACT_ADDRESS

npx hardhat run scripts/seed.js --network localhost
```

---

## 3. Mobile App (Expo)

### 3.1 Install Dependencies

```bash
cd mobile
npm install
npx expo install expo-camera expo-barcode-scanner expo-location expo-network @react-native-async-storage/async-storage axios
```

### 3.2 Start Dev Server

```bash
npx expo start
```

Scan the QR code with Expo Go on your phone, or press:
- `a` — Android emulator
- `i` — iOS simulator (macOS only)
- `w` — web browser (limited camera support)

### 3.3 Verify

1. Grant camera permission when prompted
2. Press "Start Scanning"
3. Point at a QR code containing `SERIAL|BATCH_ID` (e.g., `BATCH-A-0001|BATCH-A`)
4. Result shows verified/flagged/prompt status

### 3.4 Offline Mode

- Disconnect network → scan → scan is queued locally
- Reconnect → queue auto-flushes within 30 seconds
- Offline banner shows queue count

---

## 4. Full Stack (All in Docker)

For a fully containerized environment (no local Python needed):

```bash
docker compose up --build
```

This starts all four services:
- **Redis** (port 6379)
- **Hardhat (anvil)** (port 8545)
- **Backend** (port 8000)

### E2E Tests

```bash
set ANTIFAKE_E2E=1
uv run pytest tests/test_e2e.py -v
```

Scenarios:
1. Scan valid serial in correct region → `"verified"`
2. Scan batch-B serial in Myanmar → `"flagged"` (GPS mismatch)
3. Scan same serial 4 times as consumer → `"prompt"` on 4th (density)

---

## 5. Enterprise API

Generate an API key:
```bash
curl -X POST http://localhost:8000/api/v1/enterprise/keys
# {"api_key": "af_270b8d62365765c9fc9816ab566bd4d5"}
```

Create a batch (returns Dual-Layer QR images as base64):
```bash
curl -X POST http://localhost:8000/api/v1/enterprise/batch \
  -H "X-API-Key: af_..." \
  -H "Content-Type: application/json" \
  -d '{"batch_id": "BATCH-D", "serials": ["S1", "S2"], "region": "MYANMAR"}'
```

---

## Quick Reference

```bash
# Dev workflow (recommended)
docker compose up -d redis hardhat     # start deps
uv run uvicorn app.main:app --reload   # start backend (hot-reload)

# Testing
uv run pytest . --cov -v               # no deps needed (fakeredis)
npx hardhat test                        # no deps needed

# Full stack
docker compose up --build               # everything in containers

# Production deploy checklist
# see docs/architecture.md → Deployment
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection. Set to `fakeredis` for tests (auto-detected). |
| `RPC_URL` | `http://localhost:8545` | EVM RPC endpoint. |
| `CONTRACT_ADDRESS` | `""` | Deployed AntiFakeBatch address (set after deploy). |
| `MOCK_GPS` | `None` | Override GPS in dev: `21.9731,96.0836`. |
| `VELOCITY_MAX_KMH` | `120.0` | Speed threshold. |
| `DENSITY_THRESHOLD_CONSUMER` | `3` | Max scans before consumer prompt. |
| `ANTIFAKE_SEED` | `true` | Auto-run seed on startup. |
| `ANTIFAKE_E2E` | `""` | Set to `1` to enable e2e tests. |

---

## CI Pipeline

```yaml
backend:  ruff check → ruff format --check → mypy → pytest --cov (80% min)
contracts: hardhat compile → hardhat test
```

Configured in `.github/workflows/ci.yml`.
