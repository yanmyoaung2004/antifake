# AntiFake APICTA — Concept & Build Plan

## The Big Idea

Stop medicine counterfeits by turning a phone camera into a forensic tool. Not by checking barcodes or holograms — those get copied. But by analyzing the *physical fingerprint* of the print itself.

---

## The Demo (90 seconds that wins)

The judge holds two identical-looking medicine boxes.

**Box A (real):** Scan QR → phone switches to macro mode → analyzes the microscopic noise pattern embedded in the print → **green pulse** → "Authentic. This is an original factory print."

**Box B (fake):** Scan QR → phone analyzes → screen flashes **red** → red heatmap overlay highlights the pixel bleeding where the photocopier smeared the noise pattern → "Counterfeit. Print quality deviation detected."

Without touching the phone, the screen shows both results on a supply chain map. Box A has a route: Factory → Distributor → Pharmacy. Box B has nothing — it was never minted.

---

## Core Concept

### Crypto-Anchor (the secret sauce)

Every genuine medicine box gets a **dual-layer QR code** at the factory:

- **Layer 1 (public):** Regular QR. Encodes batch ID + serial number. Any phone can read it.
- **Layer 2 (private):** A high-density random noise pattern printed *inside* the QR's quiet zone. This pattern is the "anchor."

The anchor's behavior when copied:
- Laser printer at factory: crisp, sharp edges, predictable noise distribution.
- Photocopier or home printer: microscopic pixel bleeding, edge softening, noise distortion.
- The difference is measurable with basic computer vision — no AI training needed.

### Anchoring (factory side)

Before printing, the factory generates the noise pattern using a seeded random algorithm. The seed is derived from the batch ID + serial number. This means:
- Every box gets a unique pattern
- The pattern is deterministic — the backend can regenerate it to compare
- No need to store images for every box, just the seed

### Verification (consumer side)

1. Phone scans Layer 1 QR → reads batch ID + serial
2. Phone takes a close-up photo of Layer 2 area
3. Backend regenerates the expected noise pattern from the seed
4. Backend compares the photo against the expected pattern:
   - Edge detection → measure sharpness of noise boundaries
   - Histogram comparison → is the noise distribution correct?
   - Pixel bleed ratio → are edges smeared?
5. If deviation > threshold → counterfeit flag
6. If clean → check supply chain (optional for MVP)

---

## Why This Wins APICTA

| Criteria | How AntiFake scores |
|---|---|
| **Innovation** | Crypto-anchor is not a blockchain QR or a hologram. It's a novel physical-digital binding. |
| **Social impact** | Counterfeit medicine kills 1M+ people/year. This is directly life-saving. |
| **Technical complexity** | Phone camera + CV + supply chain data. Sounds hard, demo feels like magic. |
| **Feasibility** | No ML training needed. Edge detection + histogram comparison works on first day. |
| **Demo-ability** | Judges hold the boxes. They see the result with their own eyes. Unforgettable. |

---

## Build Plan (Step by Step, Zero to Hero)

### Phase 1: The Magic Trick (Week 1)

Goal: Get the core demo working. Two boxes, one phone, one backend call.

Day 1:
- Set up Python project with FastAPI
- Write `POST /api/v1/verify` endpoint
- Receives: `{batch_id, serial, image_base64}`
- Returns: `{status, confidence, message}`
- No database, no Redis. Just CV logic.

Day 2:
- Implement crypto-anchor verification logic:
  - `generate_anchor(seed) -> np.array` — creates expected noise pattern
  - `extract_noise(image) -> np.array` — crops Layer 2 from photo
  - `compare(expected, actual) -> float` — edge sharpness + histogram + pixel bleed
- Threshold tuning: test against a real print vs a phone photo of a print

Day 3:
- Build the comparison visualization:
  - Generate a heatmap overlay showing where the counterfeit deviates
  - Return as base64 overlay image alongside the verdict
- Test end-to-end with sample images

Day 4:
- Build a minimal React Native (Expo) app:
  - One screen
  - Camera view with QR scanning
  - Auto-switch to macro mode when QR is detected
  - Send image to backend
  - Display result: green check or red X with heatmap overlay

Day 5:
- Polish the demo flow:
  - Loading animation while analyzing
  - Smooth transition from scan to result
  - The "heatmap reveal" as the dramatic moment
- Create reference images: print one "good" anchor, photocopy it for "bad"

Deliverable: A working phone app that can tell a real print from a copy.

---

### Phase 2: The Demo Story (Week 2)

Goal: Build the physical demo kit and script.

- Print 5 medicine box mockups with real crypto-anchors (laser printer)
- Print 5 with photocopied anchors (same printer, second generation)
- Build a small box that holds both + a phone mount (for trade show)
- Write the 90-second demo script. Rehearse it.
- Record a backup video in case live demo fails.

---

### Phase 3: The Supply Chain Layer (Week 3)

Goal: Add the "journey" visual to the result screen.

- Simple batch registry: `{batch_id, serial, region}` stored in JSON or SQLite
- After verification, look up batch and display:
  - Route map: Factory → Port → Distributor → Pharmacy
  - If no batch found: "This serial was never registered"
- No blockchain. No Redis. A flat file or Postgres.

---

### Phase 4: Competition Prep (Week 4)

Goal: Everything looks and feels like a shipped product.

- UI polish: animations, color scheme, typography
- Presentation slides: problem → solution → demo → impact
- Backup plan: pre-recorded demo video + live backup phone
- Prepare answers for: "Why not blockchain?" "What if the phone has no camera?" "How do you onboard factories?"

---

## Tech Stack (Minimum, No Overengineering)

| Layer | Choice | Why |
|---|---|---|
| Backend | Python + FastAPI | Fast to build, easy to demo |
| CV | OpenCV + NumPy | Edge detection, histograms, pixel math. No ML. |
| Mobile | React Native (Expo) | One codebase, easy camera access |
| Storage | JSON files or SQLite | No Docker, no Redis, no blockchain |
| Deployment | Local network or public cloud | Whatever works for the demo venue |

---

## The One Rule

Never add something to the codebase that isn't needed for the demo. The demo is the product. Everything else is noise.
