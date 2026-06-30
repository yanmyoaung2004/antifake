# AntiFake — Product Specification and Architecture

This document is the single source of truth for product intent, architecture constraints, and development roadmap for a closed-loop anti-counterfeit verification system.

**Stack:** React Native (mobile app) + Python/FastAPI (backend) + EVM blockchain (notary) + Redis (cache + scan state).

---

The fundamental flaw in your original plan was that it relied on a **static asset** (the packaging) to verify a **dynamic journey**. Once a counterfeiter clones the static asset, your system breaks.

To fix this, we must transition from passive scanning to an **Active Challenge-Response** and **Anomaly Detection** model. Here is the upgraded architecture and development plan.

---

## 1. Upgraded Technical Architecture

Instead of just checking if a barcode or hologram looks right, the app will analyze the _behavior_ of the supply chain and use non-clonable cryptographic triggers.

### Phase 1: Serialization via Crypto-Anchors (The Factory Side)

Instead of standard barcodes or static holograms , you must convince your enterprise partners to adopt **Dual-Layer QR codes** or **Secure Graphic Micro-structures** (Crypto-anchors).

- **Layer 1 (Public):** A standard QR code containing the product's batch ID and routing info.
- **Layer 2 (Private/Physical):** A high-density, randomized noise pattern printed inside or next to the QR code. This pattern suffers from "optical degradation" when copied. If a counterfeiter copies it with a high-end printer, the microscopic pixel bleeding changes the digital signature. Your Python backend's computer vision can instantly flag this degradation as a fake.

### Phase 2: Spatial-Temporal Anomaly Detection (The Backend Engine)

Your Python backend must run a real-time analytics pipeline to catch cloned authentic codes. Every time a user scans a product, the backend evaluates three vectors:

1. **Velocity Check:** If a product with the unique ID `MED-10293` is scanned in Yangon, Myanmar, and then again in Bangkok, Thailand 45 minutes later, it is physically impossible for the same medicine package to have traveled that fast. Flag both packages.
2. **Density Check:** If a unique retail package item is scanned more than 3 times by different individual consumer accounts, the system flags it as a "replayed code" and moves it to the **Community Shield** database automatically.
   - **False-positive escalation:** Scanning >3 times is normal for downstream roles (pharmacist checks inbound stock, regulator audits, consumer verifies). The app separates scan roles via account type. A pharmacy wholesaler scanning 100 units receives a "bulk import" role flag and is exempt from replay logic. If a single consumer account triggers the threshold, the system prompts: _"This code has been reported before. Report counterfeits or verify authenticity?"_ — the user can submit a photo for manual review instead of being blocked.

3. **IP/GPS Cross-Reference:** Cross-check the phone’s GPS location against the expected regional distribution path logged on your ledger replica. If a batch meant exclusively for Vietnam is being scanned in Mandalay, it indicates a leaked or compromised batch.

---

## 2. Updated Database & Smart Contract Design

To handle this without crashing your 3-second time limit, restructure how data flows through your backend and blockchain layers:

```
                  ┌────────────────────────────────────────┐
                  │  Factory: Mints Batch NFT / Event Logs │
                  └───────────────────┬────────────────────┘
                                      │ (Asynchronous Write)
                                      ▼
                  ┌────────────────────────────────────────┐
                  │       Ethereum / EVM Blockchain        │
                  └───────────────────┬────────────────────┘
                                      │ (Continuous Sync)
                                      ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        AntiFake Backend System                         │
│                                                                        │
│   ┌───────────────────────────┐         ┌──────────────────────────┐   │
│   │  The Graph / Local Index  │         │   Redis Cache Cluster    │   │
│   │ (Validates Supply History)│         │ (Tracks Active Scan Cores)   │
│   └─────────────┬─────────────┘         └────────────┬─────────────┘   │
└─────────────────┼────────────────────────────────────┼─────────────────┘
                  │                                    │
                  └─────────────────┬──────────────────┘
                                    ▼
                     ┌──────────────────────────────┐
                     │ 3-Second Aggregator Decision │
                     └──────────────────────────────┘

```

- **The Blockchain Layer:** Treat the blockchain purely as a notary. The factory publishes a Merkle Root of all valid serialized items in a batch.

- **The Cache Layer (Redis):** Each physical package carries a globally unique serial number (not just a batch ID). Example: `PHARMA-BATCH-09A3-UNIT-8812`.
- `Key: item:<serial_number>:scan_count`
- `Key: item:<serial_number>:last_gps`
- `Key: item:<serial_number>:last_scan_ts`

- When a consumer scans, the app hits Redis first. If `scan_count > 1`, the app immediately triggers an advanced multi-point visual inspection check or prompts the user: _"This item has been scanned before. Are you opening a fresh box?"_

---

## 3. Offline and Partial-Connectivity Design

Pharmaceutical supply chains frequently operate in low-connectivity environments. The app must degrade gracefully:

- **Offline scan queue:** Scans are stored locally with a timestamp and GPS snapshot (last known location). On reconnect, the queue flushes to the backend for batch verification.
- **Stale-data fallback:** If Redis or the blockchain indexer is unreachable, the app falls back to a local allowlist of known-good batch roots (pulled during last online sync). Verification degrades to "batch-level" authenticity only — spatial-temporal checks are deferred.
- **No-network UI:** If a product has never been seen before and no network is available, the app shows: _"Cannot verify — connect to the internet to check this code for the first time."_ Previously scanned codes show a cached result with a "last verified" timestamp.

---

## 4. Dev Environment, Testing, and Local Development

### Local net and seed data

- Use **Ganache** or **Hardhat** for a local EVM chain in dev. Factory mint transactions go to this chain.
- A `seed.py` script generates synthetic batch data: 500 serialized units across 3 batches, with known-good crypto-anchor fingerprints and pre-assigned distribution paths.
- Redis is run locally via Docker or a mock (`fakeredis` for unit tests).

### Testing strategy

- **Anomaly engine tests:** Unit-test velocity, density, and GPS-cross checks without real GPS or Redis by injecting synthetic scan event arrays directly into the decision function. Each test supplies a list of `(serial, lat, lng, timestamp, role)` tuples and asserts the verdict.
- **Integration tests:** A local Docker Compose stack (FastAPI + Redis + Hardhat node) exercises the full scan flow. Use `httpx.AsyncClient` against the FastAPI test client.
- **"Fake GPS" dev toggle:** A query parameter `?mock_gps=21.9731,96.0836` in dev mode overrides the phone's reported location for testing regional distribution checks without traveling to Myanmar.
- **CI pipeline order:** `ruff check . && ruff format --check . && mypy . && pytest --cov --cov-fail-under=80`

---

## 5. Revised Development Roadmap

To pull this off with your small team (AI Expert, Pharma Expert, Full-Stack Developer), you need to prioritize tasks efficiently:

### Sprint 5-6: The Local Optimization (Full-Stack Dev + AI Expert)

- Implement native image cropping in React Native using `react-native-vision-camera`.
- Train your Python computer vision model _specifically_ on identifying print texture anomalies and structural geometric alignment, rather than just recognizing standard barcodes.

### Sprint 7-8: The Velocity Backend (AI Expert + Pharma Expert)

- Build the Redis tracking logic into your FastAPI framework.
- The Pharma Expert maps out standard regional distribution paths (e.g., Factory -> Distributor -> Pharmacy) to establish the rule-based boundaries for the anomaly engine.

### Sprint 9+ : Enterprise API Rollout

- Instead of waiting for an enterprise to completely change their packaging, provide them with an API that integrates with their existing industrial packaging printers to generate your dual-layer anti-counterfeit codes.
