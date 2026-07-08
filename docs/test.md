# AntiFake v2 — Testing Guide

## 1. Unit Tests

```bash
cd backend
.venv\Scripts\python.exe -m pytest -v
```

Expected: **32 passed**

Test breakdown:

| File | Tests | Coverage |
|---|---|---|
| `test_anchor.py` | 8 | CV anchor generation + comparison + endpoint |
| `test_enhanced.py` | 4 | Batch lookup, velocity alerts, map data |
| `test_preprocess.py` | 8 | QR detection, anchor extraction, photo degradation |
| `test_https.py` | 2 | Self-signed cert + HTTPS server |
| `test_partner_api.py` | 6 | Register, list, idempotency, route replacement |
| `test_samples.py` | 2 | Pre-generated genuine + tampered PNGs |
| `test_verify.py` | 2 | Health endpoint + full HTTP roundtrip |

### Accuracy Benchmark

```bash
cd backend
.venv\Scripts\python.exe tools/benchmark.py
```

Expected:
```
Accuracy:         100.0%
Precision:        100.0%
Recall:           100.0%
```

The benchmark generates 50 genuine and 50 counterfeit crypto-anchors and tests all 100 through the API. Detection is 100% on the synthetic test set.

### Robustness Tests

**Transformed 64×64 anchors (no QR, no pipeline):**

```bash
.venv\Scripts\python.exe tools/robustness_test.py
```

Applies 14 real-world transforms (blur, noise, resize, rotation, photocopy) to clean anchors. Current: **10/14 genuine pass**, all 4 fakes caught.

**Simulated phone photos (full pipeline with QR detection + preprocessing):**

```bash
.venv\Scripts\python.exe tools/photo_robustness.py
```

Synthesizes 13 phone-photo scenarios (blur, rotation, perspective, lighting, photocopy) and runs them through the full `preprocess_photo` + `compare_anchors` pipeline. The CV is best-effort here — the spatial-temporal and hash chain checks remain the authoritative signals.

---

## 2. Core CV tests

| Test | What it checks |
|---|---|
| `test_same_seed_produces_same_pattern` | Deterministic anchor generation |
| `test_different_seeds_produce_different_patterns` | Unique anchors per serial |
| `test_output_is_correct_shape` | Anchor is 64x64 uint8 |
| `test_identical_anchors_pass` | Same anchor → not degraded |
| `test_different_anchors_flag` | Different anchor → degraded |
| `test_noisy_image_flags` | Random noise → degraded |
| `test_valid_anchor_returns_verified` | API returns verified for good image |
| `test_tampered_anchor_returns_counterfeit` | API returns counterfeit for bad image |

## 3. Sample image tests

| Test | What it checks |
|---|---|
| `test_genuine_sample_verifies` | Pre-generated genuine PNG works |
| `test_tampered_sample_flags` | Pre-generated tampered PNG caught |

## 4. API health

| Test | What it checks |
|---|---|
| `test_health` | Health endpoint works |
| `test_verify_returns_verified_for_valid_image` | Full HTTP roundtrip |

## 5. Enhanced features (batch + velocity + map)

| Test | What it checks |
|---|---|
| `test_verify_returns_batch_info` | Verified scan includes batch metadata + 4 route points |
| `test_second_scan_shows_velocity_alert` | Same serial scanned twice from different cities triggers velocity warning |
| `test_unknown_batch_returns_no_batch_info` | Unregistered batch still verifies anchor but returns null batch_info |
| `test_counterfeit_still_returns_batch_info` | Counterfeit detection preserves batch info from registry |

## 6. Photo preprocessing

| Test | What it checks |
|---|---|
| `test_detects_qr_in_clean_photo` | QR detector returns 4 ordered corners |
| `test_returns_none_for_no_qr` | No QR → returns None (no false positives) |
| `test_clean_photo_extracts_perfect_anchor` | Axis-aligned photo → NCC=1.0 |
| `test_unknown_seed_falls_back` | Without expected, falls back to bbox crop |
| `test_no_qr_returns_none` | Pure noise → None |

## 7. HTTPS

| Test | What it checks |
|---|---|
| `test_cert_files_exist` | cert.pem + key.pem are valid PEM |
| `test_server_responds_over_https` | `/api/v1/health` works over TLS |

## 8. Partner API

| Test | What it checks |
|---|---|
| `test_register_new_batch` | New batch → inserted=True |
| `test_register_idempotent_update` | Re-register → inserted=False, message="updated" |
| `test_list_batches` | Returns all registered batches |
| `test_register_replaces_route` | Re-register replaces old route points |
| `test_register_rejects_missing_required` | Pydantic returns 422 for missing fields |
| `test_registered_batch_appears_in_verify` | Verify response includes manufacturer + drug_name |

---

## 9. Hash chain

| Endpoint | What it checks |
|---|---|
| `GET /api/v1/chain/verify?serial=X` | Verifies SHA256 chain integrity for all scans of serial X |
| Chain badge in web UI | Green 🔗 if chain intact, red 🔓 if tampered |

---

## 10. HTTPS

The HTTPS suite requires cert.pem and key.pem in the backend root. Generate once with:

```bash
.venv\Scripts\python.exe tools/generate_cert.py
```

---

## 11. Test with Python (No Phone Needed)

Start the backend first:

```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Then in another terminal:

### Genuine anchor — returns `verified` with batch info

```powershell
.venv\Scripts\python.exe -c "import httpx, base64; b64 = base64.b64encode(open('sample_images/genuine_BATCH-A_001.png','rb').read()).decode(); r = httpx.post('http://localhost:8765/api/v1/verify', json={'batch_id':'BATCH-A','serial':'001','image_base64':b64,'lat':16.8661,'lng':96.1951,'timestamp':'2026-07-09T10:00:00'}); d=r.json(); print('Status:', d['status']); print('Drug:', d.get('batch_info',{}).get('drug_name')); print('Manufacturer:', d.get('batch_info',{}).get('manufacturer')); print('Route points:', len(d.get('batch_info',{}).get('route',[])))"
```

Expected:
```
Status: verified
Drug: Paracetamol 500mg
Manufacturer: PharmaCorp Myanmar Ltd.
Route points: 4
```

### Velocity alert — scan same serial twice

```powershell
.venv\Scripts\python.exe -c "
import httpx, base64, sqlite3
con = sqlite3.connect('antifake.db'); con.execute('DELETE FROM scans'); con.commit(); con.close()
b64 = base64.b64encode(open('sample_images/genuine_BATCH-A_001.png','rb').read()).decode()

r1 = httpx.post('http://localhost:8765/api/v1/verify', json={'batch_id':'BATCH-A','serial':'TEST-V','image_base64':b64,'lat':16.8661,'lng':96.1951,'timestamp':'2026-07-09T10:00:00'})
print('Scan 1 — count:', r1.json()['scan_history']['scan_count'])

r2 = httpx.post('http://localhost:8765/api/v1/verify', json={'batch_id':'BATCH-A','serial':'TEST-V','image_base64':b64,'lat':21.9731,'lng':96.0836,'timestamp':'2026-07-09T10:30:00'})
d2 = r2.json()
print('Scan 2 — count:', d2['scan_history']['scan_count'], '| alert:', 'YES' if d2['scan_history'].get('velocity_alert') else 'none')
"
```

Expected:
```
Scan 1 — count: 1
Scan 2 — count: 2 | alert: YES
```

### Counterfeit with batch info

```powershell
.venv\Scripts\python.exe -c "import httpx, base64; b64 = base64.b64encode(open('sample_images/tampered_BATCH-A_001.png','rb').read()).decode(); r = httpx.post('http://localhost:8765/api/v1/verify', json={'batch_id':'BATCH-A','serial':'001','image_base64':b64,'lat':16.8661,'lng':96.1951,'timestamp':'2026-07-09T10:00:00'}); d=r.json(); print('Status:', d['status']); print('Batch:', d.get('batch_info',{}).get('batch_id')); print('Overlay:', 'YES' if d.get('overlay_base64') else 'none')"
```

Expected:
```
Status: counterfeit
Batch: BATCH-A
Overlay: YES
```

### Partner registration

```powershell
.venv\Scripts\python.exe tools/onboard_partner.py
```

Imports 5 representative partner batches. Verify any of them:

```powershell
.venv\Scripts\python.exe -c "import httpx; r = httpx.post('http://localhost:8765/api/v1/verify', json={'batch_id':'MM-PARA-2026-07','serial':'X1','lat':16.8661,'lng':96.1951,'timestamp':'2026-07-09T00:00:00'}); d=r.json(); print('Status:', d['status']); print('Drug:', d['batch_info']['drug_name']); print('Manufacturer:', d['batch_info']['manufacturer']); print('Route points:', len(d['batch_info']['route']))"
```

---

## 12. Web Interface (Drag & Drop)

```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open `http://localhost:8765` in any browser.

**Steps:**
1. Click the drop zone or drag an image file onto it
2. Adjust GPS coordinates (defaults to Yangon)
3. Click **Verify**
4. Result shows: badge + metrics + supply chain route on interactive map + velocity alerts

Phones: the file input has `capture="environment"` so you can take a photo directly with the rear camera.

For QR scanning, use HTTPS (camera access requires it):

```bash
.venv\Scripts\python.exe tools/run_https.py
```

---

## 13. Physical Demo (Phone + Printed Boxes)

```bash
.venv\Scripts\python.exe tools/printable_labels.py
```

Print `demo_labels/label_*.png` on sticker paper. Attach one to each of two identical medicine boxes. Scan with phone camera or upload a photo to the web interface.

---

## 14. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` | Run `uv pip install -e ".[dev]"` |
| Backend won't start | Check port 8765 is free: `netstat -ano \| findstr :8765`. Windows reserves 7997–8096 (Hyper-V) — pick any other port. |
| Database errors | Delete `antifake.db` and restart the server |
| No route shown on map | Run `.venv\Scripts\python.exe seed/seed_data.py` to populate batch data |
| Camera/QR scanner blocked | Use HTTPS: `.venv\Scripts\python.exe tools/run_https.py` |
| `cryptography` not installed | `.venv\Scripts\python.exe -m pip install cryptography` |
| Velocity alert not showing | The same serial needs to be scanned twice with different GPS within minutes |
