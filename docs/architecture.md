# AntiFake — Architecture

## Overview

AntiFake is a closed-loop anti-counterfeit verification system for pharmaceuticals. It combines physical crypto-anchors (dual-layer QR codes) with spatial-temporal anomaly detection to verify a product's journey through the supply chain.

**Stack:** React Native (Expo) + Python/FastAPI + EVM blockchain (Hardhat) + Redis

---

## System Diagram

```
                    ┌────────────────────────────────────────┐
                    │  Factory: Mints Batch NFT / Event Logs │
                    └───────────────────┬────────────────────┘
                                        │ (Asynchronous Write)
                                        ▼
                    ┌────────────────────────────────────────┐
                    │       Ethereum / EVM Blockchain        │
                    │     (Notary — Merkle Root Storage)     │
                    └───────────────────┬────────────────────┘
                                        │ (Continuous Sync)
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                         AntiFake Backend System                          │
 │                                                                          │
 │    ┌───────────────────────────┐         ┌──────────────────────────┐    │
 │    │  Blockchain Client (Web3) │         │   Redis Cache Cluster    │    │
 │    │ (Validates Supply History)│         │ (Scan Counters + GPS)    │    │
 │    └─────────────┬─────────────┘         └────────────┬─────────────┘    │
 └──────────────────┼────────────────────────────────────┼──────────────────┘
                    │                                    │
                    └─────────────────┬──────────────────┘
                                      ▼
                       ┌──────────────────────────────┐
                       │  Orchestrator (3 Checkers)   │
                       │  velocity + density + gps    │
                       │        + crypto-anchor       │
                       └──────────────┬───────────────┘
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │    POST /api/v1/scan → JSON  │
                       └──────────────────────────────┘
                                      ▲
                                      │
                    ┌─────────────────┴──────────────────┐
                    │     React Native (Expo) App        │
                    │  Camera Scan → GPS → API call      │
                    │  Offline Queue → AsyncStorage      │
                    └────────────────────────────────────┘
```

---

## Directory Structure

```
antifake/
├── backend/                  # Python/FastAPI backend
│   ├── app/
│   │   ├── main.py           # FastAPI app entrypoint, lifespan
│   │   ├── config.py         # Pydantic settings (env-based)
│   │   ├── schemas.py        # Pydantic request/response models
│   │   ├── router/
│   │   │   ├── scan.py       # POST /api/v1/scan
│   │   │   ├── health.py     # GET /api/v1/health
│   │   │   └── enterprise.py # POST /api/v1/enterprise/batch
│   │   ├── engine/
│   │   │   ├── orchestrator.py  # Runs all checks, aggregates verdict
│   │   │   ├── velocity.py      # Haversine distance / time → speed check
│   │   │   ├── density.py       # Redis scan counter with role thresholds
│   │   │   └── gps.py           # Polygon boundary check per batch region
│   │   ├── crypto/
│   │   │   ├── anchor.py     # OpenCV pixel-bleed detection on Layer 2
│   │   │   └── merkle.py     # Merkle proof generation/verification
│   │   └── blockchain/
│   │       └── client.py     # Web3 client for contract interaction
│   ├── tests/
│   │   ├── conftest.py       # Fixtures: fake Redis, test client
│   │   ├── test_velocity.py  # Impossible speed, plausible, no prior
│   │   ├── test_density.py   # Consumer threshold, wholesaler exempt
│   │   ├── test_gps.py       # Inside/outside region, unknown batch
│   │   ├── test_orchestrator.py # Full pipeline combinations
│   │   ├── test_scan_api.py  # HTTP roundtrip
│   │   ├── test_main.py      # App lifecycle
│   │   ├── test_enterprise.py # API key + batch creation
│   │   └── test_e2e.py       # Full integration (requires ANTIFAKE_E2E=1)
│   ├── seed/
│   │   └── seed.py           # Generates 500 serials, regions, fingerprints
│   ├── pyproject.toml
│   └── Dockerfile
├── contracts/                # Solidity smart contracts
│   ├── contracts/
│   │   └── AntiFakeBatch.sol # Batch minting, Merkle verification, scan events
│   ├── test/
│   │   └── AntiFakeBatch.test.js  # 6 tests: mint, duplicate, auth, scan, Merkle
│   ├── scripts/
│   │   ├── deploy.js         # Deploy to any Hardhat network
│   │   └── seed.js           # Mint 3 batches with 500 serials
│   ├── hardhat.config.js
│   └── package.json
├── mobile/                   # React Native (Expo) app
│   ├── App.tsx               # Entry: tab navigation + offline sync
│   ├── src/
│   │   ├── screens/
│   │   │   ├── ScanScreen.tsx     # Camera, QR scan, GPS, API call
│   │   │   ├── ResultScreen.tsx   # Status badge, report submission
│   │   │   ├── HistoryScreen.tsx  # Past scans, pull-to-refresh
│   │   │   └── SettingsScreen.tsx # App info
│   │   ├── services/
│   │   │   ├── api.ts            # Axios client, POST /api/v1/scan
│   │   │   ├── offlineQueue.ts   # AsyncStorage queue, flush on reconnect
│   │   │   └── location.ts       # Expo location permission + GPS
│   │   ├── components/
│   │   │   ├── CameraView.tsx    # Expo Camera with barcode scanner
│   │   │   ├── ScanResultCard.tsx # Colored status card
│   │   │   └── OfflineBanner.tsx  # Queue length indicator
│   │   └── utils/
│   │       ├── storage.ts        # AsyncStorage wrapper
│   │       └── constants.ts      # API URL, storage keys
├── docker-compose.yml        # Redis + Hardhat (anvil) + Backend
├── .github/workflows/ci.yml  # Ruff → mypy → pytest (backend), compile → test (contracts)
├── product.md                # Product specification (source of truth)
├── plan.md                   # Implementation plan
├── manual-task.md            # Human vs agent task breakdown
└── AGENTS.md                 # Agent instruction file
```

---

## Core Data Flow

### Scan Lifecycle

1. **Mobile app** opens camera, scans QR (Layer 1) → extracts `serial` + `batch_id`
2. Captures GPS coordinates via `expo-location`
3. If available, captures close-up photo of Layer 2 noise pattern
4. Calls `POST /api/v1/scan` with `{serial, batch_id, lat, lng, timestamp, role, crypto_image?}`
5. **Backend orchestrator** runs 4 checks in parallel:
   - **Velocity:** Haversine distance between current and last scan GPS / elapsed hours → km/h. If > 120 km/h, flags as impossible.
   - **Density:** Redis `INCR scan_count`. Consumer > 3 scans → soft prompt. Wholesaler never flags.
   - **GPS Cross-Reference:** Checks if lat/lng falls within the batch's assigned distribution region polygon.
   - **Crypto-Anchor:** If image provided, runs OpenCV edge detection to measure pixel bleed. Degraded → flagged.
6. **Aggregation:**
   - Any `FLAG` → `"flagged"` (confidence 0.0)
   - Density `FLAG_PROMPT` only → `"prompt"` (confidence 0.5)
   - All pass → `"verified"` (confidence 1.0)
7. Backend stores `last_lat`, `last_lng`, `last_scan_ts` in Redis for future velocity checks
8. Scan event recorded on-chain via Web3 (fire-and-forget)

### Offline Flow

- No network? Scan is saved to AsyncStorage queue
- On reconnect (checked every 30s via `expo-network`), queue is flushed in FIFO order
- Previously scanned items show cached result with "last verified" timestamp
- First-time scans without network show "Cannot verify — connect to internet"

---

## Key Architecture Decisions

| Decision | Rationale |
|---|---|
| **Redis for scan state** | Sub-millisecond latency for velocity/density checks. Avoids blockchain latency for real-time checks. |
| **Blockchain as notary only** | Merkle root per batch, not per-scan. Gas costs stay low. Events indexed by The Graph for audit trail. |
| **Fakeredis for testing** | Zero-infrastructure unit tests. Switch to real Redis via `REDIS_URL` env var in production. |
| **Polygon boundary check** | Simple rect-based check for MVP. Pluggable to GeoJSON + point-in-polygon for complex territories. |
| **Role-based density exemption** | Wholesalers scanning 100s of units should not trigger replay alarms. Consumer-only threshold. |
| **Crypto-anchor as optional** | MVP works with QR-only scan. Anchor verification is incremental value-add. |

---

## Batch + Serial ID Scheme

Each physical package carries a globally unique serial: `PHARMA-BATCH-09A3-UNIT-8812`

Redis keys:
- `item:<serial>:scan_count` — density counter
- `item:<serial>:last_lat` — last scan latitude
- `item:<serial>:last_lng` — last scan longitude
- `item:<serial>:last_scan_ts` — last scan ISO timestamp

Test seed data: 500 serials across 3 batches (BATCH-A: Myanmar, BATCH-B: Vietnam, BATCH-C: Thailand).

---

## Deployment

### Production Checklist

- [ ] Switch `fakeredis` → Redis cluster with TLS
- [ ] Add JWT-based consumer auth + API key for enterprise
- [ ] Structured JSON logging
- [ ] Deploy `AntiFakeBatch.sol` to Sepolia, verify on Etherscan
- [ ] Mobile code-signing + app store listing
- [ ] Deploy The Graph subgraph indexing `ScanRecorded` events

### CI Pipeline

```yaml
backend: ruff check → ruff format --check → mypy → pytest --cov (80% min)
contracts: hardhat compile → hardhat test
```
