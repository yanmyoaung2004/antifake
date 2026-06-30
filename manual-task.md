# AntiFake — Manual Tasks (Human Must Execute)

This file lists every task from `plan.md` that requires a human. The agent generates source code; you run commands, install toolchains, and handle interactive or environment-dependent steps.

---

## Prerequisites — Install These First

| Tool | Version | Check with |
|---|---|---|
| Python | >= 3.12 | `python --version` |
| Node.js | >= 20 | `node --version` |
| npm | >= 10 | `npm --version` |
| Docker | latest | `docker --version` |
| Docker Compose | v2 | `docker compose version` |
| Git | any | `git --version` |
| Hardhat | (installed per project) | — |
| React Native CLI | (installed per project) | — |

Windows notes:
- Use `py -3.12` instead of `python3`.
- Use `npx.cmd` instead of `npx` if needed.
- For React Native Android: install Android Studio + SDK. For iOS: Xcode (macOS only).

---

## Phase 0 — Monorepo Scaffold

| # | Who | What | When |
|---|---|---|---|
| 0.0 | **Human** | `git init` the repo and create the root `antifake/` directory if not already done. | Start |
| 0.1 | Agent | Writes: `.gitignore`, `docker-compose.yml`, `.github/workflows/ci.yml` | After 0.0 |
| 0.2 | **Human** | Review committed files. Run `git add . && git commit -m "chore: scaffold monorepo"`. | After 0.1 |

---

## Phase 1 — Smart Contracts

| # | Who | What | When |
|---|---|---|---|
| 1.0 | **Human** | `cd contracts && npm init -y` | After 0.2 |
| 1.1 | **Human** | `npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox` | After 1.0 |
| 1.2 | **Human** | `npx hardhat init` — choose "Create an empty hardhat.config.js". Answer NO to all optional prompts. | After 1.1 |
| 1.3 | Agent | Writes: `contracts/contracts/AntiFakeBatch.sol`, `contracts/test/AntiFakeBatch.test.js`, `contracts/hardhat.config.js` | After 1.2 |
| 1.4 | **Human** | `cd contracts && npx hardhat compile` — verify no errors. | After 1.3 |
| 1.5 | **Human** | `cd contracts && npx hardhat test` — verify all tests pass. | After 1.4 |
| 1.6 | Agent | Writes: `contracts/scripts/deploy.js`, `contracts/scripts/seed.js` | After 1.5 |
| 1.7 | **Human** | Run deploy + seed on localhost hardhat node: open separate terminal, run `npx hardhat node`, then `npx hardhat run scripts/deploy.js --network localhost && npx hardhat run scripts/seed.js --network localhost`. Save the deployed contract address. | After 1.6 |
| 1.8 | **Human** | `git add . && git commit -m "feat: add AntiFakeBatch contract"` | After 1.7 |

---

## Phase 2 — Backend

| # | Who | What | When |
|---|---|---|---|
| 2.0 | **Human** | `cd backend && py -3.12 -m venv .venv && .venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Mac/Linux) | After 1.8 |
| 2.1 | **Human** | `pip install fastapi uvicorn[standard] redis fakeredis web3 pillow opencv-python-headless numpy pytest httpx pytest-asyncio pytest-cov ruff mypy pydantic-settings` | After 2.0 |
| 2.2 | Agent | Writes all backend files: `pyproject.toml`, `app/__init__.py`, `app/main.py`, `app/config.py`, `app/schemas.py`, `app/router/__init__.py`, `app/router/scan.py`, `app/router/health.py`, `app/engine/__init__.py`, `app/engine/velocity.py`, `app/engine/density.py`, `app/engine/gps.py`, `app/engine/orchestrator.py`, `app/crypto/__init__.py`, `app/crypto/anchor.py`, `app/crypto/merkle.py`, `app/blockchain/__init__.py`, `app/blockchain/client.py`, `tests/__init__.py`, `tests/conftest.py`, `tests/test_velocity.py`, `tests/test_density.py`, `tests/test_gps.py`, `tests/test_orchestrator.py`, `tests/test_scan_api.py`, `seed/__init__.py`, `seed/seed.py`, `Dockerfile` | After 2.1 |
| 2.3 | **Human** | `cd backend && ruff check .` — fix any lint errors. | After 2.2 |
| 2.4 | **Human** | `cd backend && mypy .` — fix any type errors. | After 2.3 |
| 2.5 | **Human** | `cd backend && pytest --cov --cov-fail-under=80` — all tests must pass. If not, report to agent. | After 2.4 |
| 2.6 | **Human** | `cd backend && uvicorn app.main:app --reload` — verify `GET /api/v1/health` returns 200. | After 2.5 |
| 2.7 | **Human** | `git add . && git commit -m "feat: add FastAPI backend with anomaly engine"` | After 2.6 |

---

## Phase 3 — Frontend (React Native)

| # | Who | What | When |
|---|---|---|---|
| 3.0 | **Human** | `npx @react-native-community/cli init AntiFakeMobile --template react-native-template-typescript` — this creates `mobile/` directory. **Note:** This requires Android SDK (Windows) or Xcode (macOS). If setup fails, use Expo as fallback. | After 2.7 |
| 3.1 | **Human** | `cd mobile && npm install react-native-vision-camera react-native-qrcode-svg @react-native-async-storage/async-storage react-native-geolocation-service axios` | After 3.0 |
| 3.2 | Agent | Writes all mobile source files: `src/App.tsx`, `src/navigation/RootNavigator.tsx`, `src/screens/ScanScreen.tsx`, `src/screens/ResultScreen.tsx`, `src/screens/HistoryScreen.tsx`, `src/screens/SettingsScreen.tsx`, `src/services/api.ts`, `src/services/offlineQueue.ts`, `src/services/location.ts`, `src/components/CameraView.tsx`, `src/components/ScanResultCard.tsx`, `src/components/OfflineBanner.tsx`, `src/utils/storage.ts`, `src/utils/constants.ts` | After 3.1 |
| 3.3 | **Human** | `cd mobile && npx react-native run-android` (or `run-ios`) — verify the app builds and opens. | After 3.2 |
| 3.4 | **Human** | `git add . && git commit -m "feat: add React Native mobile app"` | After 3.3 |

---

## Phase 4 — Integration

| # | Who | What | When |
|---|---|---|---|
| 4.0 | Agent | Updates `docker-compose.yml` if needed, adds FastAPI lifespan event for seed, writes e2e test script. | After 3.4 |
| 4.1 | **Human** | `docker compose build` — verify no build errors. | After 4.0 |
| 4.2 | **Human** | `docker compose up -d` — start all services. | After 4.1 |
| 4.3 | **Human** | `curl http://localhost:8000/api/v1/health` — verify backend responds. | After 4.2 |
| 4.4 | **Human** | Manual e2e smoke test — use curl or Postman to hit `POST /api/v1/scan` with test payloads from `plan.md` §4.2. Confirm "verified", "flagged", and "prompt" responses. | After 4.3 |
| 4.5 | **Human** | `docker compose logs` — check for any errors. | After 4.4 |
| 4.6 | **Human** | Push CI workflow: create `.github/workflows/ci.yml` (already written by agent in phase 0). Push to GitHub, verify CI passes. | After 4.5 |
| 4.7 | **Human** | `git add . && git commit -m "feat: integration stack and e2e tests"` | After 4.6 |

---

## Phase 5 — Enterprise API & Deploy Prep

| # | Who | What | When |
|---|---|---|---|
| 5.0 | Agent | Writes enterprise batch endpoint `app/router/enterprise.py`, API key middleware. | After 4.7 |
| 5.1 | **Human** | `cd backend && pytest --cov` — confirm no regressions. | After 5.0 |
| 5.2 | **Human** | Production checklist — execute each item: | After 5.1 |
| 5.2a | **Human** | Switch Redis to production cluster with TLS. Update `docker-compose.yml` and config. | |
| 5.2b | **Human** | Add JWT auth for mobile consumers. Enterprise API key auth (agent writes middleware, human generates keys). | |
| 5.2c | **Human** | Enable structured JSON logging. | |
| 5.2d | **Human** | Deploy contract to Sepolia testnet. Save deployed address. Fund deployer wallet. | |
| 5.2e | **Human** | React Native code-signing setup + app store listing. | |
| 5.2f | **Human** | Deploy The Graph subgraph indexing `ScanRecorded` events. | |
| 5.3 | **Human** | `git add . && git commit -m "feat: enterprise API and deploy prep"` | After 5.2 |

---

## Summary — What the Agent Handles

The agent writes every source file. You handle toolchain setup, dependency installation, and running/debugging commands.

| Component | Agent writes | Human runs |
|---|---|---|
| Config files | .gitignore, docker-compose.yml, CI, pyproject.toml, hardhat.config.js | npm init, pip install |
| Smart contracts | AntiFakeBatch.sol, deploy.js, seed.js, tests | hardhat compile, hardhat test, hardhat node |
| Backend (Python) | All 20+ files (app/, engine/, crypto/, blockchain/, tests/, seed/, Dockerfile) | venv, pip install, ruff, mypy, pytest, uvicorn |
| Frontend (TS/TSX) | All 14 files (screens/, services/, components/, utils/) | npx react-native init, npm install, run-android |
| Integration | Docker Compose, e2e test script | docker compose up, curl smoke test |
| Enterprise API | Enterprise endpoint, API key middleware | pytest, deploy ops |

**If tests fail or builds break:** paste the error output to the agent. It will fix the code and ask you to re-run.
