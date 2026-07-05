# AntiFake v2 — Testing Guide

## 1. Unit Tests

```bash
cd version2\backend
.venv\Scripts\activate
uv run pytest -v
```

Expected: **12 passed**

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
| `test_genuine_sample_verifies` | Pre-generated genuine PNG works |
| `test_tampered_sample_flags` | Pre-generated tampered PNG caught |
| `test_health` | Health endpoint works |
| `test_verify_returns_verified_for_valid_image` | Full HTTP roundtrip |

---

## 2. Test with Curl/Python (No Phone Needed)

Start the backend first:

```bash
uv run uvicorn app.main:app --reload
```

Then in another terminal:

### Genuine anchor — should return `verified`

```powershell
python -c "import httpx, base64; b64 = base64.b64encode(open('sample_images/genuine_BATCH-A_001.png','rb').read()).decode(); r = httpx.post('http://localhost:8000/api/v1/verify', json={'batch_id':'BATCH-A','serial':'001','image_base64':b64}); print(r.json())"
```

Expected output:

```json
{"status":"verified","confidence":1.0,"message":"Anchor pattern matches. Authentic.",...}
```

### Tampered anchor — should return `counterfeit`

```powershell
python -c "import httpx, base64; b64 = base64.b64encode(open('sample_images/tampered_BATCH-A_001.png','rb').read()).decode(); r = httpx.post('http://localhost:8000/api/v1/verify', json={'batch_id':'BATCH-A','serial':'001','image_base64':b64}); print(r.json())"
```

Expected output:

```json
{"status":"counterfeit","confidence":0.44,"message":"Print quality deviation detected...","overlay_base64":"..."}
```

### Test each metric manually

```powershell
python -c "
import httpx, base64
# Genuine
b64 = base64.b64encode(open('sample_images/genuine_BATCH-A_001.png','rb').read()).decode()
r = httpx.post('http://localhost:8000/api/v1/verify', json={'batch_id':'BATCH-A','serial':'001','image_base64':b64})
m = r.json()['metrics']
print('Genuine:  edge_diff=%s  hist_corr=%s  bleed=%s  confidence=%s' % (m['edge_diff_ratio'], m['hist_correlation'], m['bleed_ratio'], m['confidence']))

# Tampered
b64 = base64.b64encode(open('sample_images/tampered_BATCH-A_001.png','rb').read()).decode()
r = httpx.post('http://localhost:8000/api/v1/verify', json={'batch_id':'BATCH-A','serial':'001','image_base64':b64})
m = r.json()['metrics']
print('Tampered: edge_diff=%s  hist_corr=%s  bleed=%s  confidence=%s' % (m['edge_diff_ratio'], m['hist_correlation'], m['bleed_ratio'], m['confidence']))
"
```

Expected:

```
Genuine:  edge_diff=1.0  hist_corr=1.0  bleed=0.0  confidence=1.0
Tampered: edge_diff=1.031  hist_corr=-0.202  bleed=0.608  confidence=0.44
```

---

## 3. Physical Demo (Phone + Printed Boxes)

### Print the labels

```bash
uv run python tools/printable_labels.py
```

Print `demo_labels/label_*.png` on sticker paper. Attach one to each of two identical medicine boxes.

### Scan with phone

1. Start both backend and mobile app
2. Open Expo Go, scan the QR code
3. Press "Start Scanning"
4. Point at the QR on the **genuine** box → you should see "AUTHENTIC" with green check
5. Point at the QR on the **counterfeit** box → you should see "COUNTERFEIT" with red X and a heatmap overlay

### Backup: Scan with laptop webcam

Open `http://localhost:8000` in a browser on your laptop (if a web demo page is available).

---

## 4. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` | Run `uv pip install -e ".[dev]"` |
| Backend won't start | Check port 8000 is free: `netstat -ano | findstr :8000` |
| Phone can't connect to Expo | Run `npx expo start --tunnel` or use curl instead |
| `curl` not recognized | Use `python -c "..."` commands above instead |
| All tampered tests pass but demo fails | Re-run `uv run python tools/printable_labels.py` to regenerate labels |
