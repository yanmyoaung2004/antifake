# AntiFake

Closed-loop anti-counterfeit verification for pharmaceutical supply chains.

**Stack:** React Native (Expo) + Python/FastAPI + EVM blockchain (Hardhat) + Redis

---

## Quick Start

```bash
# Backend
cd backend
uv venv .venv && .venv\Scripts\activate && uv pip install -e ".[dev]"
uv run uvicorn app.main:app --reload

# Smart contracts
cd contracts && npm install && npx hardhat test

# Mobile (in another terminal)
cd mobile && npm install && npx expo start

# Full stack with Docker
docker compose up
```

---

## Architecture

| Layer | Tech | Role |
|---|---|---|
| Mobile | React Native (Expo) | Camera QR scan, GPS, offline queue |
| Backend | Python/FastAPI | Anomaly engine (velocity, density, GPS), crypto-anchor CV |
| Blockchain | Solidity/Hardhat | Merkle-root batch minting, scan event notary |
| Cache | Redis | Scan counters, last-GPS state (sub-ms lookups) |

See [`docs/architecture.md`](docs/architecture.md) for data flow, directory map, and key decisions.

---

## Setup

Detailed setup steps for each component: [`docs/setup.md`](docs/setup.md)

---

## Project State

| Component | Status | Quality |
|---|---|---|
| Backend | ✅ Implemented | 19 tests, 86% coverage, 0 lint/type errors |
| Contracts | ✅ Implemented | 6 tests, compile clean |
| Mobile | ✅ Implemented | TypeScript: 0 errors |
| CI | ✅ Configured | ruff → mypy → pytest (backend), compile → test (contracts) |
| E2E | ✅ Written | `ANTIFAKE_E2E=1` for full integration tests |

---

## Documents

| File | Purpose |
|---|---|
| [`product.md`](product.md) | Product specification, architecture decisions, roadmap |
| [`plan.md`](plan.md) | Implementation plan (5 phases, 20+ tasks) |
| [`manual-task.md`](manual-task.md) | Human vs agent task breakdown |
| [`AGENTS.md`](AGENTS.md) | Agent instruction file |
| [`docs/architecture.md`](docs/architecture.md) | System architecture and data flow |
| [`docs/setup.md`](docs/setup.md) | Step-by-step setup guide |
