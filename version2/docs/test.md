# AntiFake v2 — Testing Guide

## 1. Unit Tests

```bash
cd version2\backend
.venv\Scripts\activate
uv run pytest -v
```

Expected: **16 passed**

### Core CV tests

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

### Sample image tests

| Test | What it checks |
|---|---|
| `test_genuine_sample_verifies` | Pre-generated genuine PNG works |
| `test_tampered_sample_flags` | Pre-generated tampered PNG caught |

### API health

| Test | What it checks |
|---|---|
| `test_health` | Health endpoint works |
| `test_verify_returns_verified_for_valid_image` | Full HTTP roundtrip |

### Enhanced features (batch + velocity + map)

| Test | What it checks |
|---|---|
| `test_verify_returns_batch_info` | Verified scan includes batch metadata + 4 route points |
| `test_second_scan_shows_velocity_alert` | Same serial scanned twice from different cities triggers velocity warning |
| `test_unknown_batch_returns_no_batch_info` | Unregistered batch still verifies anchor but returns null batch_info |
| `test_counterfeit_still_returns_batch_info` | Counterfeit detection preserves batch info from registry |

---

## 2. Test with Python (No Phone Needed)

Start the backend first:

```bash
uv run uvicorn app.main:app --reload
```

Then in another terminal:

### Genuine anchor — returns `verified` with batch info

```powershell
uv run python -c "import httpx, base64; b64 = base64.b64encode(open('sample_images/genuine_BATCH-A_001.png','rb').read()).decode(); r = httpx.post('http://localhost:8000/api/v1/verify', json={'batch_id':'BATCH-A','serial':'001','image_base64':b64,'lat':16.8661,'lng':96.1951,'timestamp':'2026-07-06T10:00:00'}); d=r.json(); print('Status:', d['status']); print('Batch:', d.get('batch_info',{}).get('batch_id'), d.get('batch_info',{}).get('region')); print('Route points:', len(d.get('batch_info',{}).get('route',[])))"
```

Expected:
```
Status: verified
Batch: BATCH-A MYANMAR
Route points: 4
```

### Velocity alert — scan same serial twice

```powershell
uv run python -c "
import httpx, base64, sqlite3, os
# Clean DB for clean test
con = sqlite3.connect('antifake.db'); con.execute('DELETE FROM scans'); con.commit(); con.close()
b64 = base64.b64encode(open('sample_images/genuine_BATCH-A_001.png','rb').read()).decode()

# Scan 1 — Yangon
r1 = httpx.post('http://localhost:8000/api/v1/verify', json={'batch_id':'BATCH-A','serial':'TEST-V','image_base64':b64,'lat':16.8661,'lng':96.1951,'timestamp':'2026-07-06T10:00:00'})
print('Scan 1 — count:', r1.json()['scan_history']['scan_count'])

# Scan 2 — Mandalay 30 min later (570 km)
r2 = httpx.post('http://localhost:8000/api/v1/verify', json={'batch_id':'BATCH-A','serial':'TEST-V','image_base64':b64,'lat':21.9731,'lng':96.0836,'timestamp':'2026-07-06T10:30:00'})
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
uv run python -c "import httpx, base64; b64 = base64.b64encode(open('sample_images/tampered_BATCH-A_001.png','rb').read()).decode(); r = httpx.post('http://localhost:8000/api/v1/verify', json={'batch_id':'BATCH-A','serial':'001','image_base64':b64,'lat':16.8661,'lng':96.1951,'timestamp':'2026-07-06T10:00:00'}); d=r.json(); print('Status:', d['status']); print('Batch:', d.get('batch_info',{}).get('batch_id')); print('Overlay:', 'YES' if d.get('overlay_base64') else 'none')"
```

Expected:
```
Status: counterfeit
Batch: BATCH-A
Overlay: YES
```

---

## 3. Web Interface (Drag & Drop)

```bash
uv run uvicorn app.main:app --reload
```

Open `http://localhost:8000` in any browser.

**Steps:**
1. Click the drop zone or drag an image file onto it
2. Adjust GPS coordinates (defaults to Yangon)
3. Click **Verify**
4. Result shows: badge + metrics + supply chain route on interactive map + velocity alerts

Phones: the file input has `capture="environment"` so you can take a photo directly with the rear camera.

---

## 4. Physical Demo (Phone + Printed Boxes)

```bash
uv run python tools/printable_labels.py
```

Print `demo_labels/label_*.png` on sticker paper. Attach one to each of two identical medicine boxes. Scan with phone camera or upload a photo to the web interface.

---

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` | Run `uv pip install -e ".[dev]"` |
| Backend won't start | Check port 8000 is free: `netstat -ano | findstr :8000` |
| Database errors | Delete `antifake.db` and restart the server |
| No route shown on map | Run `uv run python seed/seed_data.py` to populate batch data |
| Expo Go can't connect | Use the web interface instead: `http://localhost:8000` |
| Velocity alert not showing | The same serial needs to be scanned twice with different GPS within minutes |
