# Changelog

## Phase 1-3 (2026-07-09)

### Phase 1 — Real-Phone Photo Preprocessing

The original CV module worked on clean 64×64 anchors but failed on real phone photos — even mild blur (σ=0.8 in a 600×400 label) caused 9/14 robustness cases to false-positive as counterfeit.

**What changed:**
- New `app/crypto/preprocess.py` pipeline: detect printed QR with `cv2.QRCodeDetector`, derive anchor position from a sub-pixel template offset, crop 64×64 with a 9×9 NCC refinement
- Anchor changed to 16×16 unique values on 4×4 blocks (64×64 total) — coarse noise that survives mild camera blur
- Comparison metrics rewritten: block NCC, edge sharpness ratio, histogram, FFT, bleed
- `simulate_photocopy` updated to actually damage block edges
- New `tests/test_preprocess.py` (8 tests)

**Result:** 5/14 → 10/14 robustness on transformed anchors. 100% benchmark accuracy preserved. Photo simulation is best-effort (spatial-temporal + hash chain remain the authoritative signal).

### Phase 2 — HTTPS Support

Camera access (`getUserMedia`) requires HTTPS in browsers. The QR scanner was unusable on phones over HTTP.

**What changed:**
- `tools/generate_cert.py` — one-command self-signed cert with SANs for localhost, antifake.local, 127.0.0.1, 0.0.0.0
- `tools/run_https.py` — convenience wrapper that auto-generates certs and starts uvicorn with `--ssl-keyfile` / `--ssl-certfile`
- `cryptography` added to dev dependencies
- `tests/test_https.py` (2 tests) validates cert + HTTPS server
- `docs/setup.md` updated with full HTTPS section including iOS/Android cert trust instructions
- `cert.pem` and `key.pem` added to `.gitignore`

### Phase 3 — Partner API + Realistic Data

Demo data was hardcoded in `seed_data.py` with no way to onboard real partners.

**What changed:**
- `POST /api/v1/register` — idempotent batch registration with full route + drug metadata
- `GET /api/v1/batches` — list all registered batches (for partner dashboards)
- New batch fields: `manufacturer`, `drug_name`, `drug_use`, `expiry`
- `seed/seed_data.py` now includes manufacturer names and drug info
- `tools/onboard_partner.py` — imports 5 representative partner batches (Myanmar, Vietnam, Thailand) with realistic drug names and geographically accurate supply chain points
- Web UI now uses server-side drug info instead of hardcoded lookup
- `tests/test_partner_api.py` (6 tests) for register, list, idempotency, route replacement, validation, verify flow

**Result:** End-to-end demo verified: partner batch → velocity alert → counterfeit detection all working.

---

## Baseline (pre-Phases 1-3)

- Custom SHA256 hash chain (no external blockchain)
- 16 unit tests
- 100-sample benchmark: 100% accuracy on synthetic
- 14-condition robustness: 5/14 genuine pass (now 10/14)
- 3 seeded batches: BATCH-A (Myanmar), BATCH-B (Vietnam), BATCH-C (Thailand)
- PWA with drag-drop photo, jsQR scanner, Leaflet.js map
- Optional Expo mobile app
