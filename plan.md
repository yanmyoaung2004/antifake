# AntiFake — Implementation Plan

## Phase 0 — Monorepo Scaffold

### 0.1 Root structure

```
antifake/
├── backend/           # Python/FastAPI
├── contracts/         # Solidity/Hardhat
├── mobile/            # React Native
├── docker-compose.yml
├── .github/workflows/ci.yml
├── AGENTS.md
├── product.md
├── plan.md
├── .gitignore
└── README.md
```

### 0.2 `.gitignore`

```
__pycache__/
node_modules/
dist/
build/
.env
*.pyc
.nyc_output/
coverage/
hardhat/cache/
hardhat/artifacts/
```

### 0.3 `docker-compose.yml`

```yaml
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  hardhat:
    image: ghcr.io/foundry-rs/foundry:latest
    command: anvil --host 0.0.0.0 --port 8545
    ports: ["8545:8545"]
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - REDIS_URL=redis://redis:6379
      - RPC_URL=http://hardhat:8545
      - CONTRACT_ADDRESS=0x...
    depends_on: [redis, hardhat]
```

### 0.4 CI — `.github/workflows/ci.yml`

Trigger: push to main, PRs.

```yaml
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install -e "backend[dev]"
      - run: ruff check backend/
      - run: ruff format --check backend/
      - run: mypy backend/
      - run: pytest backend/ --cov --cov-fail-under=80

  contracts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: "20"}
      - run: npm ci
        working-directory: contracts
      - run: npx hardhat compile
        working-directory: contracts
      - run: npx hardhat test
        working-directory: contracts
```

---

## Phase 1 — Smart Contracts (`contracts/`)

### Task 1.1 Init Hardhat project

```
cd contracts
npm init -y
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox
npx hardhat init
```

### Task 1.2 `contracts/AntiFakeBatch.sol`

- **`BatchMinted` event** — emitted during factory minting, stores batch ID, Merkle root of all valid serials, distribution region hash, timestamp.
- **`verifySerial(bytes32 batchId, string serial, bytes32[] proof)`** — verifies a serial against the batch's Merkle root. Pure view function, no gas for consumers.
- **`recordScan(bytes32 batchId, string serial, address scanner, bytes32 gpsHash)`** — emits a `ScanRecorded` event for The Graph indexer. Only callable by the backend signer.

Files:

```
contracts/contracts/AntiFakeBatch.sol
contracts/test/AntiFakeBatch.test.js
contracts/hardhat.config.js
```

### Task 1.3 Deploy script + Hardhat task

- `contracts/scripts/deploy.js` — deploys `AntiFakeBatch`, logs address.
- `contracts/scripts/seed.js` — mints 3 batches on localnet, each with 100–200 serials, writes output JSON for `seed.py` to consume.

---

## Phase 2 — Backend (`backend/`)

### Task 2.1 Python project scaffold

```
cd backend
py -3.12 -m venv .venv
pip install fastapi uvicorn[standard] redis fakeredis
pip install web3 pillow opencv-python-headless numpy
pip install pytest httpx pytest-asyncio pytest-cov ruff mypy
```

`backend/pyproject.toml`:

```toml
[project]
name = "antifake-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi", "uvicorn[standard]", "redis", "fakeredis",
    "web3", "pillow", "opencv-python-headless", "numpy",
]

[project.optional-dependencies]
dev = [
    "pytest", "httpx", "pytest-asyncio", "pytest-cov",
    "ruff", "mypy",
]

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### Task 2.2 Directory structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── router/
│   │   ├── __init__.py
│   │   ├── scan.py
│   │   └── health.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── velocity.py
│   │   ├── density.py
│   │   ├── gps.py
│   │   └── orchestrator.py
│   ├── crypto/
│   │   ├── __init__.py
│   │   ├── anchor.py
│   │   └── merkle.py
│   └── blockchain/
│       ├── __init__.py
│       └── client.py
├── tests/
│   ├── __init__.py
│   ├── test_velocity.py
│   ├── test_density.py
│   ├── test_gps.py
│   ├── test_orchestrator.py
│   ├── test_scan_api.py
│   └── conftest.py
├── seed/
│   └── seed.py
├── Dockerfile
└── pyproject.toml
```

### Task 2.3 `app/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379"
    rpc_url: str = "http://localhost:8545"
    contract_address: str = ""
    mock_gps: str | None = None
    velocity_max_kmh: float = 120.0
    density_threshold_consumer: int = 3
    density_threshold_wholesaler: int = 0
```

### Task 2.4 Anomaly engine — `app/engine/`

**`velocity.py`**:
- `check_velocity(serial, lat, lng, ts, redis) -> Verdict`
- Fetch `last_gps` and `last_scan_ts` from Redis.
- Compute Haversine distance / time delta → km/h.
- If speed > `velocity_max_kmh` (configurable, default 120 km/h), return `FLAG`.
- Returns `PASS` if no prior scan exists.

**`density.py`**:
- `check_density(serial, role, redis) -> Verdict`
- `INCR scan_count` in Redis.
- If `role == "wholesaler"`, never flag (bulk import exemption).
- If `role == "consumer"` and count > `density_threshold_consumer`, return `FLAG_PROMPT` (soft flag — UI shows prompt, not block).
- Returns `PASS` otherwise.

**`gps.py`**:
- `check_gps(batch_id, lat, lng) -> Verdict`
- Batch distribution regions stored as polygon boundaries (GeoJSON in Redis/DB).
- If `lat, lng` is outside any assigned region for this batch, return `FLAG`.
- Region polygons are defined in `seed.py` and loaded at startup.

**`orchestrator.py`**:
- `evaluate_scan(serial, batch_id, lat, lng, ts, role, crypto_image) -> ScanResult`
- Runs all three checks in parallel (asyncio.gather).
- Runs crypto-anchor check in parallel.
- If any check returns `FLAG`, final decision is `FLAG`.
- If density returns `FLAG_PROMPT`, final decision is `FLAG_PROMPT`.
- Computes final confidence score: `1.0` if all pass, `0.0` if any flag, `0.5` if prompt.

### Task 2.5 Crypto-anchor verification — `app/crypto/`

**`anchor.py`**:
- `verify_anchor(image_bytes: bytes) -> AnchorResult`
- Accept uploaded image of Layer 2 (noise pattern).
- Run OpenCV template matching against known-good pattern for this batch.
- Compute pixel-bleed metric: ratio of edge pixels exceeding intensity threshold.
- If bleed ratio > threshold, return `DEGRADED` (likely counterfeit).
- First version: simple histogram comparison + edge detection. No ML training needed for MVP.

**`merkle.py`**:
- `generate_proof(serial, serials_list) -> bytes32[]`
- `verify_proof(serial, proof, merkle_root) -> bool`
- Used by the contract, but backend also uses it to verify before submitting a scan tx.

### Task 2.6 API — `app/router/scan.py`

```
POST /api/v1/scan
Body: {
  serial: str,
  batch_id: str,
  lat: float,
  lng: float,
  timestamp: str (ISO8601),
  role: "consumer" | "wholesaler" | "regulator",
  crypto_image: base64 (optional)
}
Response: {
  status: "verified" | "flagged" | "prompt" | "error",
  confidence: float,
  message: str,
  cached: bool,
  last_verified: str | null
}
```

- Calls `orchestrator.evaluate_scan(...)`.
- If `mock_gps` setting is set, overrides `lat, lng` in dev.
- Records scan on-chain via `blockchain.client.record_scan(...)` (async, fire-and-forget with retry).

### Task 2.7 Blockchain client — `app/blockchain/client.py`

- `get_batch_root(batch_id) -> bytes32` — queries contract.
- `verify_serial_onchain(batch_id, serial, proof) -> bool` — calls contract.
- `record_scan(batch_id, serial, gps_hash)` — sends tx via backend signer.

### Task 2.8 Seed script — `seed/seed.py`

- Generates 500 serials across 3 batches: `BATCH-A`, `BATCH-B`, `BATCH-C`.
- Assigns distribution regions (Myanmar, Vietnam, Thailand) as polygon boundaries.
- Generates known-good crypto-anchor fingerprints (random noise images, stored as base64).
- Writes seed JSON to `seed/data/`.

### Task 2.9 Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e .
COPY app/ app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Task 2.10 Tests

**`tests/test_velocity.py`**:
```
scenarios: impossible speed, plausible speed, no prior scan
input: list of (lat, lng, ts) tuples
each test: inject via fakeredis, run check_velocity, assert PASS/FLAG
```

**`tests/test_density.py`**:
```
scenarios: consumer 1st scan, consumer 4th scan, wholesaler 100th scan
each test: inject scan_count in fakeredis, assert PASS/FLAG_PROMPT/PASS
```

**`tests/test_gps.py`**:
```
scenarios: inside region, outside region, unknown batch
each test: load region polygons, run check_gps, assert PASS/FLAG
```

**`tests/test_orchestrator.py`**:
```
scenarios: all checks pass → verified
  one check fails → flagged
  density prompt only → prompt
  crypto anchor degraded → flagged
```

**`tests/test_scan_api.py`**:
```
using TestClient, fakeredis
full HTTP roundtrip: POST /api/v1/scan, assert response shape + status code
```

**`tests/conftest.py`**:
```
fixtures:
  - test_client -> TestClient(app)
  - fake_redis -> fakeredis.FakeStrictRedis()
  - override app dependency to use fake_redis
  - seed_polygons -> mock region data
```

---

## Phase 3 — Frontend (`mobile/`)

### Task 3.1 Init React Native project

```
npx @react-native-community/cli init AntiFakeMobile --template react-native-template-typescript
cd mobile
npm install react-native-vision-camera react-native-qrcode-svg
npm install @react-native-async-storage/async-storage
npm install react-native-geolocation-service
npm install axios
```

### Task 3.2 Directory structure

```
mobile/
├── src/
│   ├── App.tsx
│   ├── navigation/
│   │   └── RootNavigator.tsx
│   ├── screens/
│   │   ├── ScanScreen.tsx
│   │   ├── ResultScreen.tsx
│   │   ├── HistoryScreen.tsx
│   │   └── SettingsScreen.tsx
│   ├── services/
│   │   ├── api.ts
│   │   ├── offlineQueue.ts
│   │   └── location.ts
│   ├── components/
│   │   ├── CameraView.tsx
│   │   ├── ScanResultCard.tsx
│   │   └── OfflineBanner.tsx
│   └── utils/
│       ├── storage.ts
│       └── constants.ts
└── __tests__/
```

### Task 3.3 Scan flow — `ScanScreen.tsx`

1. Open camera view via `react-native-vision-camera`.
2. Detect Dual-Layer QR: scan QR (Layer 1) → extract `serial`, `batch_id`.
3. If `crypto_image` expected, take close-up photo of Layer 2 area.
4. Capture GPS from `react-native-geolocation-service`.
5. Show spinner. Call `POST /api/v1/scan`.
6. On failure (network), push to offline queue (AsyncStorage).

### Task 3.4 Offline queue — `offlineQueue.ts`

- `enqueue(scanPayload)` — stores in AsyncStorage array.
- `flushQueue()` — on app foreground / network restored, POST each payload in FIFO order.
- `getQueueLength()` — for badge display.

### Task 3.5 Result screen — `ResultScreen.tsx`

- Displays `status` badge (green check / red flag / yellow prompt).
- Shows confidence score, message, "last verified" timestamp.
- If `FLAG_PROMPT`: shows textarea + camera button to submit photo for manual review.

### Task 3.6 History — `HistoryScreen.tsx`

- Reads from local cache (AsyncStorage).
- Shows scrollable list of past scans with status and timestamp.
- Pull-to-refresh re-checks any pending items with the backend.

---

## Phase 4 — Integration

### Task 4.1 Wire Docker Compose

- `docker-compose up` starts all four services (redis, hardhat, backend).
- `seed.py` runs once on backend startup via FastAPI lifespan event.
- Backend health endpoint: `GET /api/v1/health` returns redis + rpc connectivity.

### Task 4.2 End-to-end test

```
scenario:
  1. Deploy contract to Hardhat (via deploy script in Dockerfile entrypoint).
  2. Seed 3 batches.
  3. Scan serial from Batch A in Yangon → expect "verified".
  4. Scan same serial 3 more times as consumer → expect "prompt" on 4th.
  5. Scan serial from Batch A in Yangon, then 45 min later in Bangkok → expect "flagged".
  6. Scan serial in Mandalay (batch assigned to Vietnam) → expect "flagged".
  7. Submit degraded crypto-anchor image → expect "flagged".
  8. Kill network, scan offline → item queued locally.
  9. Restore network → queue flushed, result synced.
```

### Task 4.3 CI verification

- `ci.yml` runs on every PR.
- Backend job: lint → typecheck → test → coverage.
- Contracts job: compile → test.

---

## Phase 5 — Enterprise API & Deploy Prep

### Task 5.1 `POST /api/v1/enterprise/batch`

- Accepts batch ID + list of serials + distribution region.
- Generates Dual-Layer QR images (Layer 1 = QR, Layer 2 = random noise pattern).
- Returns batch metadata + image assets for the enterprise packaging printer integration.
- Requires API key auth (header `X-API-Key`).

### Task 5.2 Production checklist

- [ ] Database: switch fakeredis to Redis cluster with TLS.
- [ ] Auth: add JWT-based consumer auth + API key for enterprise.
- [ ] Monitoring: structured JSON logs, health endpoint.
- [ ] Contract: deploy to testnet (Sepolia), verify on Etherscan.
- [ ] Mobile: code-signing setup, stores listing prep.
- [ ] The Graph: deploy subgraph indexing `ScanRecorded` events.
