# AntiFake v1 — Architecture

## Overview

Version 1 is a full-stack closed-loop anti-counterfeit verification system. It combines physical crypto-anchors (dual-layer QR codes) with spatial-temporal anomaly detection to verify a product's journey through the supply chain.

**Stack:** React Native (Expo) + Python/FastAPI + Solidity/Hardhat (EVM) + Redis

---

## Tools & Libraries

| Layer | Tool | Purpose |
|---|---|---|
| Backend framework | FastAPI + Uvicorn | Async Python HTTP server |
| Computer vision | OpenCV + NumPy | Edge detection, pixel bleed analysis, heatmap |
| Blockchain | Web3.py + Hardhat + Solidity | Merkle-root batch minting, scan event notary |
| Cache | Redis + fakeredis | Sub-ms scan counters and GPS state |
| Mobile | React Native (Expo) | Cross-platform app, camera, GPS |
| Camera | expo-camera | QR scanning + Layer 2 photo capture |
| GPS | expo-location | Location capture for spatial-temporal checks |
| Storage | AsyncStorage | Offline scan queue |
| HTTP | Axios, httpx | API communication |
| QR generation | qrcode (Python) | Generating Layer 1 QR codes |
| Testing | pytest, pytest-asyncio, chai, ethers | Backend + contract tests |
| Linting/typing | ruff, mypy | Code quality |
| CI | GitHub Actions | Automatic lint → typecheck → test |
| Containerization | Docker + Docker Compose | Redis, Hardhat node, backend services |
| Package management | uv | Fast Python dependency resolution |

---

## Directory Structure

```
version1/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint, lifespan events
│   │   ├── config.py                  # Pydantic settings (env-based)
│   │   ├── schemas.py                 # Request/response Pydantic models
│   │   ├── dependencies.py            # Redis connection (real or fake)
│   │   ├── router/
│   │   │   ├── scan.py                # POST /api/v1/scan
│   │   │   ├── health.py              # GET /api/v1/health
│   │   │   └── enterprise.py          # POST /api/v1/enterprise/batch + /keys
│   │   ├── engine/
│   │   │   ├── orchestrator.py        # Runs all checks in parallel, aggregates verdict
│   │   │   ├── velocity.py            # Haversine distance / time → km/h
│   │   │   ├── density.py             # Redis INCR scan counter, role thresholds
│   │   │   └── gps.py                 # Polygon boundary check per batch region
│   │   ├── crypto/
│   │   │   ├── anchor.py              # OpenCV pixel-bleed detection
│   │   │   └── merkle.py              # Merkle proof generation/verification
│   │   └── blockchain/
│   │       └── client.py              # Web3 contract interaction
│   ├── tests/
│   │   ├── conftest.py                # Fixtures: fake Redis, test client
│   │   ├── test_velocity.py           # 3 tests: impossible/plausible/no prior
│   │   ├── test_density.py            # 3 tests: consumer/wholesaler/threshold
│   │   ├── test_gps.py               # 3 tests: inside/outside/unknown
│   │   ├── test_orchestrator.py       # 3 tests: full pipeline combinations
│   │   ├── test_scan_api.py           # 2 tests: HTTP roundtrip + health
│   │   ├── test_main.py               # 2 tests: app lifecycle
│   │   ├── test_enterprise.py         # 3 tests: API key + batch creation
│   │   └── test_e2e.py               # 4 tests: full integration (requires ANTIFAKE_E2E=1)
│   ├── seed/
│   │   └── seed.py                    # Generates 500 serials, regions, fingerprints
│   ├── Dockerfile                     # Container build
│   └── pyproject.toml
├── contracts/
│   ├── contracts/
│   │   └── AntiFakeBatch.sol          # EVM contract: batch minting, Merkle, scan events
│   ├── test/
│   │   └── AntiFakeBatch.test.js      # 6 tests: mint, duplicate, auth, scan, Merkle
│   ├── scripts/
│   │   ├── deploy.js                  # Deploy to any Hardhat network
│   │   └── seed.js                    # Mint 3 batches with 500 serials
│   └── hardhat.config.js
├── mobile/
│   ├── App.tsx                        # Tab navigation, offline sync
│   ├── src/
│   │   ├── screens/
│   │   │   ├── ScanScreen.tsx         # Camera, QR scan, GPS, API call
│   │   │   ├── ResultScreen.tsx       # Status badge, report submission
│   │   │   ├── HistoryScreen.tsx      # Past scans, pull-to-refresh
│   │   │   └── SettingsScreen.tsx     # App info
│   │   ├── services/
│   │   │   ├── api.ts                # Axios client
│   │   │   ├── offlineQueue.ts       # AsyncStorage queue
│   │   │   └── location.ts           # Expo GPS
│   │   ├── components/
│   │   │   ├── CameraView.tsx        # Expo Camera + barcode scanner
│   │   │   ├── ScanResultCard.tsx    # Colored status card
│   │   │   └── OfflineBanner.tsx     # Queue count indicator
│   │   └── utils/
│   │       ├── storage.ts            # AsyncStorage wrapper
│   │       └── constants.ts          # API URL, storage keys
│   └── app.json
├── docker-compose.yml                 # Redis + Hardhat (anvil) + Backend
├── .github/workflows/ci.yml           # Ruff → mypy → pytest (backend), compile → test (contracts)
├── product.md                         # Product specification
├── plan.md                            # Implementation plan
└── manual-task.md                     # Human vs agent task breakdown
```

---

## Data Flow

### Scan Lifecycle

```
Mobile App                         Backend                         Redis / Blockchain
    │                                 │                                  │
    │  POST /api/v1/scan              │                                  │
    │  {serial, batch_id, lat,        │                                  │
    │   lng, timestamp, role,         │                                  │
    │   crypto_image?}                │                                  │
    │ ───────────────────────────────>│                                  │
    │                                 │                                  │
    │                                 │  ┌─ async gather ────────────┐   │
    │                                 │  │                            │   │
    │                                 │  │  check_velocity() ──────────>  │
    │                                 │  │  (haversine / time)        │  │
    │                                 │  │  <──────────────────────────  │
    │                                 │  │                            │   │
    │                                 │  │  check_density() ───────────>  │
    │                                 │  │  (INCR scan_count)         │  │
    │                                 │  │  <──────────────────────────  │
    │                                 │  │                            │   │
    │                                 │  │  check_gps()               │   │
    │                                 │  │  (polygon boundary)        │   │
    │                                 │  │                            │   │
    │                                 │  │  verify_anchor()           │   │
    │                                 │  │  (OpenCV pixel bleed)      │   │
    │                                 │  └────────────────────────────┘   │
    │                                 │                                  │
    │                                 │  ┌─ aggregate verdict ───────┐   │
    │                                 │  │ any FLAG → "flagged"      │   │
    │                                 │  │ density FLAG_PROMPT →     │   │
    │                                 │  │   "prompt"                │   │
    │                                 │  │ all PASS → "verified"     │   │
    │                                 │  └───────────────────────────┘   │
    │                                 │                                  │
    │                                 │  store last_lat, last_lng,       │
    │                                 │  last_scan_ts ───────────────────>│
    │                                 │                                  │
    │  <──────────────────────────────│                                  │
    │  {status, confidence, message}  │                                  │
```

### Offline Flow

```
Phone loses network
    │
    ├─ Scan payload saved to AsyncStorage queue
    │
    └─ On reconnect (every 30s poll):
         └─ queue.flush() → POST each pending scan
```

---

## Smart Contract Design

**Contract:** `AntiFakeBatch.sol`

| Function | Visibility | Gas | Purpose |
|---|---|---|---|
| `mintBatch(batchId, merkleRoot, regionHash)` | `onlyBackend` | High | Register a new batch |
| `verifySerial(batchId, serial, proof)` | `view` | None | Merkle proof verification |
| `recordScan(batchId, serial, gpsHash)` | `onlyBackend` | Medium | Record scan event |

The blockchain acts purely as a **notary** — it stores Merkle roots of all valid serials per batch. Consumers never pay gas; verification happens off-chain via the backend. The `ScanRecorded` event is indexed by The Graph for audit trails.

---

## Key Decisions

| Decision | Rationale |
|---|---|
| **Redis for scan state** | Sub-millisecond latency for velocity/density checks. Avoids blockchain write costs for real-time data. |
| **Blockchain as notary only** | Merkle root per batch, not per serial. Gas costs stay low. |
| **Fakeredis for tests** | Zero-infrastructure unit tests. Switch to real Redis via `REDIS_URL` env var. |
| **Role-based density exemption** | Wholesalers scanning 100s of units should not trigger replay alarms. Consumer-only threshold. |
| **Polygon boundary check** | Simple rect-based check for MVP. Pluggable to GeoJSON for complex territories. |
| **Crypto-anchor as optional** | MVP works with QR-only scan. Anchor verification is incremental value-add. |

---

## Testing Strategy

| Layer | Framework | Scope |
|---|---|---|
| Backend unit | pytest | Velocity, density, GPS, orchestrator, anchor |
| Backend API | httpx + ASGITransport | Full HTTP roundtrip without network |
| Backend e2e | pytest + Docker Compose | Real Redis + Hardhat node (ANTIFAKE_E2E=1) |
| Contracts | Hardhat test + chai + ethers | Mint, auth, duplicate, Merkle proofs |
| Mobile | TypeScript | tsc --noEmit compiles with zero errors |

---

## CI Pipeline

```yaml
backend:
  - ruff check
  - ruff format --check
  - mypy
  - pytest --cov (80% min)

contracts:
  - hardhat compile
  - hardhat test
```

## Deployment

```bash
docker compose up
```

Starts Redis (6379), Hardhat (8545), Backend (8000).

Production checklist:
- Switch fakeredis → Redis cluster with TLS
- Add JWT consumer auth + API key for enterprise
- JSON structured logging
- Deploy AntiFakeBatch.sol to Sepolia
- Mobile code-signing + app store
- The Graph subgraph for ScanRecorded events
