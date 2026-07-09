"""
Template-based explanation engine for the AntiFake verification result.

Produces natural-language explanations of what a verification means,
why each check passed or failed, and what the user should do next.

No LLM required — works offline, zero latency, no hallucination risk.
Explanations are structured as multi-sentence paragraphs that an
AI pharmacist assistant would say.

Architecture:
    explain(request: ExplainRequest) -> ExplainResponse
    ├── First call (empty conversation): generates a full initial
    │   explanation covering all checks, metrics, and AI confidence.
    │   Includes 3-5 follow-up suggestions.
    └── Follow-up call (user chose one): generates a targeted
        deep-dive on the specific check or metric.
"""
from __future__ import annotations

from typing import Any


def _fmt(val: Any, unit: str = "") -> str:
    """Pretty-format a number or value."""
    if val is None:
        return "N/A"
    if isinstance(val, float):
        return f"{val:.2f}{unit}"
    return f"{val}{unit}"


def _blurb_status(verify: dict) -> str:
    status = verify.get("status", "unknown")
    conf = verify.get("confidence", 0)
    drug = "this product"
    bi = verify.get("batch_info") or {}
    if bi.get("drug_name"):
        drug = bi["drug_name"]
    elif bi.get("batch_id"):
        drug = f"batch {bi['batch_id']}"

    if status == "verified":
        return (
            f"**Verified** — {drug} passed all checks "
            f"({conf:.0%} confidence). No anomalies detected. "
            "It is safe to consume."
        )
    elif status == "counterfeit":
        return (
            f"**Counterfeit detected** — {drug} failed the "
            "crypto-anchor verification. The print quality deviates from "
            "the factory original. This product should **not** be consumed. "
            "Please report it to the relevant authorities."
        )
    elif status == "flagged":
        return (
            f"**Flagged** — {drug} passed the print quality check "
            "but triggered a spatial-temporal alert. "
            f"This does not mean it's counterfeit, but further "
            "investigation is recommended."
        )
    else:
        return (
            f"**{status.title()}** — an unexpected error occurred "
            f"during verification."
        )


def _blurb_cv_metrics(verify: dict) -> str | None:
    """Explain what each crypto-anchor metric means."""
    metrics = verify.get("metrics")
    if not metrics or not isinstance(metrics, dict):
        return None
    # Don't explain raw CV values if no image was provided
    if metrics.get("note"):
        return None
    lines: list[str] = []
    # Edge sharpness ratio
    edge = metrics.get("edge_ratio") or metrics.get("edge_diff_ratio")
    if edge is not None:
        if isinstance(edge, float) and edge < 0.7:
            lines.append(
                f"• **Edge sharpness** ({edge:.2f}): The 4×4 block "
                "boundaries appear significantly blurred compared to "
                "the factory original. This is a common sign of "
                "photocopying — real factory prints have crisp edges."
            )
        elif isinstance(edge, float) and edge > 1.3:
            lines.append(
                f"• **Edge sharpness** ({edge:.2f}): The block "
                "boundaries appear sharper than expected, which may "
                "indicate image processing or an artificial generation."
            )
        elif isinstance(edge, float):
            lines.append(
                f"• **Edge sharpness** ({edge:.2f}): The 4×4 block "
                "edges match the expected sharpness, consistent with "
                "a genuine factory print."
            )
    # Histogram
    hist = metrics.get("hist_correlation")
    if hist is not None:
        lines.append(
            f"• **Histogram** ({hist:.2f}): {'Matches' if hist > 0.3 else 'Differs from'} "
            "the expected grayscale distribution. This measures whether "
            "the random noise pattern has the right statistical properties."
        )
    # Block NCC
    block = metrics.get("block_ncc")
    if block is not None:
        if block < 0.3:
            lines.append(
                f"• **Block match** ({block:.2f}): The 16×16 block pattern "
                "does not match the expected values. This means the noise "
                "pattern is different — either a different batch or a "
                "counterfeit."
            )
        else:
            lines.append(
                f"• **Block match** ({block:.2f}): The 16×16 block pattern "
                "matches the factory's deterministic seed."
            )
    # Bleed
    bleed = metrics.get("bleed_ratio")
    if bleed is not None:
        if bleed > 0.4:
            lines.append(
                f"• **Pixel bleed** ({bleed:.2f}): {bleed*100:.0f}% of "
                "pixels exceed the expected intensity difference. "
                "This indicates smearing — a characteristic of "
                "photocopied or rescanned labels."
            )
        else:
            lines.append(
                f"• **Pixel bleed** ({bleed:.2f}): Minimal intensity "
                "deviation, consistent with a fresh factory print."
            )
    # FFT
    fft_c = metrics.get("fft_correlation")
    if fft_c is not None:
        lines.append(
            f"• **Frequency match** ({fft_c:.2f}): The spatial frequency "
            "structure of the noise pattern. High values mean the "
            "pattern's overall texture is preserved."
        )
    if lines:
        return "### Crypto-Anchor Metrics\n" + "\n".join(lines)
    return None


def _blurb_ai_confidence(verify: dict) -> str | None:
    ac = verify.get("ai_confidence")
    if not ac or not isinstance(ac, dict):
        return None
    pg = ac.get("p_genuine", 0)
    pf = ac.get("p_counterfeit", 0)
    agrees = ac.get("model_agrees_with_cv")
    model = ac.get("model", "CNN")
    agree_str = (
        "and agrees with the hand-tuned CV analysis"
        if agrees
        else "and **disagrees** with the hand-tuned CV — this warrants additional scrutiny"
        if agrees is False
        else ""
    )
    return (
        f"### AI Second Opinion\n"
        f"The {model} classifier rates this as "
        f"**{pg*100:.0f}% genuine**, **{pf*100:.0f}% counterfeit** "
        f"{agree_str}."
    )


def _blurb_spatial(verify: dict) -> str | None:
    sh = verify.get("scan_history")
    if not sh or not isinstance(sh, dict):
        return None
    parts: list[str] = ["### Spatial-Temporal Checks"]
    vel = sh.get("velocity_alert")
    den = sh.get("density_alert")
    gps_a = sh.get("gps_alert")
    count = sh.get("scan_count", 0)
    prev = sh.get("previous_scan") or {}

    parts.append(f"• **Scan count**: This is scan #{count} for this serial number.")
    if vel:
        parts.append(f"• **Velocity**: ⚠ {vel}")
    else:
        parts.append("• **Velocity**: Normal travel speed.")
    if den:
        parts.append(f"• **Density**: ⚠ {den}")
    else:
        parts.append("• **Density**: Normal scan frequency.")
    if gps_a:
        parts.append(f"• **GPS**: ⚠ {gps_a}")
    elif prev:
        parts.append(f"• **GPS**: Consistent with the batch's distribution region.")

    if count > 0 and prev:
        parts.append(
            f"• **Previous scan**: Was at ({prev.get('lat', 0):.1f}, "
            f"{prev.get('lng', 0):.1f}) on "
            f"{prev.get('timestamp', 'unknown')} with result "
            f"\"{prev.get('result', 'unknown')}\"."
        )

    chain = sh.get("chain_intact")
    if chain is not None:
        chain_msg = sh.get("chain_message", "")
        parts.append(
            f"• **Chain integrity**: {'✅ Intact' if chain else '❌ Broken'} "
            f"— {chain_msg}"
        )

    return "\n".join(parts)


def _blurb_batch_info(verify: dict) -> str | None:
    bi = verify.get("batch_info")
    if not bi or not isinstance(bi, dict):
        return None
    parts: list[str] = ["### Supply Chain"]
    name = bi.get("drug_name") or bi.get("batch_id", "")
    mfr = bi.get("manufacturer", "")
    region = bi.get("region", "")
    expiry = bi.get("expiry", "")
    route = bi.get("route", [])
    if name:
        parts.append(f"• **Product**: {name}")
    if mfr:
        parts.append(f"• **Manufacturer**: {mfr}")
    if region:
        parts.append(f"• **Distribution region**: {region}")
    if expiry:
        parts.append(f"• **Expiry**: {expiry}")
    if route:
        stops = " → ".join(
            p.get("location_name", "").split("—")[0].strip()
            for p in route
        )
        parts.append(f"• **Journey**: {stops}")
    return "\n".join(parts)


def _suggested_followups(verify: dict) -> list[str]:
    """Generate 3-5 follow-up question suggestions."""
    suggestions = []

    status = verify.get("status", "")
    metrics = verify.get("metrics") or {}
    sh = verify.get("scan_history") or {}
    bi = verify.get("batch_info") or {}
    ac = verify.get("ai_confidence") or {}

    if status == "verified":
        suggestions.append("What do the crypto-anchor metrics mean?")
    elif status == "counterfeit":
        suggestions.append("What exactly made this fail the crypto-anchor check?")
        suggestions.append("How can I report this counterfeit?")
    elif status == "flagged":
        suggestions.append("Why was this flagged but not counterfeit?")
        suggestions.append("What does the velocity alert mean for safety?")

    if (
        metrics
        and isinstance(metrics, dict)
        and not metrics.get("note")
    ):
        suggestions.append("Can you explain the edge sharpness ratio?")
        suggestions.append("What is pixel bleed and why does it matter?")

    if sh.get("velocity_alert") or sh.get("density_alert") or sh.get("gps_alert"):
        suggestions.append("Tell me more about the spatial-temporal alert.")

    if ac.get("p_genuine") is not None:
        suggestions.append("How does the AI classifier work?")

    if bi.get("route"):
        suggestions.append("Where did this batch come from?")

    if sh.get("chain_intact") is not None:
        suggestions.append("What is the hash chain?")

    # Deduplicate and limit
    seen: set[str] = set()
    result: list[str] = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result[:5]


def generate_initial_explanation(verify: dict) -> dict:
    """Generate a complete initial explanation and follow-up suggestions."""
    parts: list[str] = []

    # 1. Status
    parts.append(_blurb_status(verify))

    # 2. CV metrics
    cv = _blurb_cv_metrics(verify)
    if cv:
        parts.append(cv)

    # 3. AI confidence
    ai = _blurb_ai_confidence(verify)
    if ai:
        parts.append(ai)

    # 4. Spatial-temporal
    sp = _blurb_spatial(verify)
    if sp:
        parts.append(sp)

    # 5. Batch info
    b = _blurb_batch_info(verify)
    if b:
        parts.append(b)

    return {
        "reply": "\n\n".join(parts),
        "suggestions": _suggested_followups(verify),
    }


def generate_deep_dive(verify: dict, user_message: str) -> dict:
    """Generate a targeted explanation for a specific follow-up question."""
    msg = user_message.lower()
    parts: list[str] = []
    suggestions: list[str] = []

    # Edge sharpness
    if "edge" in msg and ("sharpness" in msg or "ratio" in msg):
        parts.append(
            "**Edge sharpness ratio** compares the gradient magnitude "
            "at the 4×4 block boundaries of the printed anchor vs the "
            "expected factory pattern.\n\n"
            "A ratio near 1.0 means the block edges are as sharp as the "
            "factory original. Below 0.7 indicates significant blurring "
            "— the edges between noise blocks are smeared out, which is "
            "characteristic of photocopying or rescaling.\n\n"
            "This works because factory labels are printed with sharp "
            "microscopic boundaries between each 4×4 noise block. "
            "A photocopier cannot reproduce those precise edges — it "
            "smooths them."
        )
        suggestions.append("What about pixel bleed?")
        suggestions.append("How does the histogram check work?")

    # Pixel bleed
    elif "bleed" in msg or "pixel bleed" in msg or "smear" in msg:
        parts.append(
            "**Pixel bleed** measures what fraction of pixels in the "
            "printed anchor differ from the expected pattern by more "
            "than 30 grayscale levels.\n\n"
            "A low value (below 0.30) means the print is clean — "
            "each pixel is where it should be. A high value (above 0.40) "
            "means the noise pattern has been smeared, which happens "
            "when a label is photocopied: the toner spreads microscopically, "
            "bleeding across pixel boundaries.\n\n"
            "In our benchmark, genuine factory prints average 0.05 bleed. "
            "Photocopies average 0.45+."
        )
        suggestions.append("What is the block NCC metric?")

    # Block NCC
    elif "block" in msg and ("ncc" in msg or "match" in msg):
        parts.append(
            "**Block NCC (Normalized Cross-Correlation)** operates on "
            "the 16×16 downsampled version of the 64×64 anchor. Each "
            "4×4 block is averaged to a single value, producing a "
            "coarse 16×16 grid that is robust to mild blur.\n\n"
            "We then compute the correlation coefficient between this "
            "16×16 grid and the expected factory grid. A value close "
            "to 1.0 means the block values match the factory's "
            "deterministic seed. A value near 0 or negative means "
            "the pattern is entirely different — this is a different "
            "batch or a counterfeit.\n\n"
            "The threshold is set at 0.30: below this, the pattern "
            "is definitively wrong."
        )
        suggestions.append("How about the AI confidence score?")

    # AI / CNN
    elif "ai" in msg or "classifier" in msg or "neural" in msg or "deep" in msg or "cnn" in msg or "model" in msg:
        ac = verify.get("ai_confidence") or {}
        parts.append(
            "The **AI classifier** is a ResNet-18 convolutional neural "
            "network trained on 10,000+ synthetic anchor images. "
            "It was trained on the same `simulate_photocopy` and "
            "`random_augment` functions used in our testing pipeline, "
            "so it has seen many thousands of variations.\n\n"
            f"The model currently rates this sample as "
            f"**genuine: {ac.get('p_genuine', 0)*100:.0f}%** "
            f"and **counterfeit: {ac.get('p_counterfeit', 0)*100:.0f}%**."
        )
        if ac.get("model_agrees_with_cv") is False:
            parts.append(
                "\n\nIn this case, the AI disagrees with the hand-tuned "
                "CV. This is rare and warrants additional scrutiny — "
                "a manual inspection is recommended."
            )
        else:
            parts.append(
                "\n\nThe AI runs in parallel with the hand-tuned CV. "
                "If both agree, confidence is high. If they disagree, "
                "the system flags the ambiguity."
            )
        suggestions.append("Is the hand-tuned CV or the AI more trustworthy?")

    # Hash chain
    elif "hash" in msg or "chain" in msg or "tamper" in msg or "blockchain" in msg:
        parts.append(
            "The **hash chain** is a tamper-proof audit trail. Every "
            "scan generates a SHA-256 hash that includes the previous "
            "scan's hash for that serial number:\n\n"
            "```\nchain_hash = SHA256(serial | batch | lat | lng | "
            "timestamp | result | prev_hash)\n```\n\n"
            "If anyone edits a past scan record, its hash changes, "
            "breaking the chain for all subsequent scans. The system "
            "recomputes every hash from the first scan to the last "
            "and checks if the stored hashes still match.\n\n"
            "This provides the same cryptographic immutability as "
            "blockchain, but with zero infrastructure — no nodes, "
            "no gas fees, no network. Just SQLite and SHA-256."
        )
        suggestions.append("Can the chain be tampered with?")

    # Velocity
    elif "velocity" in msg or "speed" in msg or "movement" in msg or "far" in msg:
        parts.append(
            "**Velocity check** uses the Haversine formula to compute "
            "the great-circle distance between the current and previous "
            "scan coordinates, then divides by the elapsed time to "
            "calculate travel speed.\n\n"
            "If the speed exceeds 120 km/h, it's flagged as impossible "
            "movement — the same physical medicine box cannot be in "
            "two cities 500 km apart in 30 minutes.\n\n"
            "This catches \"code replay\" attacks where a counterfeiter "
            "scans a genuine serial from another region and tries to "
            "reuse it locally. The system sees: same serial, different "
            "city, too quickly = impossible = cloned."
        )
        suggestions.append("What is the density check?")

    # Density
    elif "density" in msg or "replay" in msg or "frequency" in msg or "too many" in msg or "count" in msg:
        parts.append(
            "**Density check** counts how many times a given serial "
            "number has been scanned. Each scan increments the counter "
            "for that serial.\n\n"
            "If the count exceeds 3 scans, the system flags a potential "
            "code replay — the same serial is being used on multiple "
            "boxes. A genuine box would only be scanned a handful of "
            "times (by the pharmacy, the patient, maybe the distributor). "
            "100 scans of the same serial likely means a counterfeit "
            "operation is reusing one valid serial."
        )
        suggestions.append("What does the GPS check do?")

    # GPS
    elif "gps" in msg or "region" in msg or "diversion" in msg or "location" in msg:
        parts.append(
            "**GPS cross-reference** checks that the scan location "
            "falls within the batch's assigned distribution region. "
            "Each batch is registered with a region (e.g., MYANMAR, "
            "VIETNAM, THAILAND) defined by a geographic bounding box.\n\n"
            "If a batch assigned to Myanmar is scanned in Thailand, "
            "the system flags it as geographic diversion — the medicine "
            "may have been diverted from its intended market. This is "
            "a common grey-market problem with pharmaceuticals."
        )
        suggestions.append("How does the supply chain map work?")

    # Supply chain
    elif "supply" in msg or "chain" in msg or "journey" in msg or "route" in msg or "batch" in msg or "came from" in msg:
        bi = verify.get("batch_info") or {}
        route = bi.get("route", [])
        if route:
            stops = "\n".join(
                f"  {i+1}. {p.get('location_name', '')} — {p.get('event', '')}"
                for i, p in enumerate(route)
            )
            parts.append(
                f"**Supply chain journey** for this batch:\n\n{stops}\n\n"
                "Each point represents a physical handoff in the "
                "distribution chain, from the factory floor to the "
                "pharmacy shelf. The map on the result page shows "
                "these as numbered markers connected by a dashed line."
            )
        else:
            parts.append(
                "This batch has no registered supply chain route. "
                "It may be from a new manufacturer that hasn't "
                "completed onboarding."
            )

    # Generic
    elif "trust" in msg or "more" in msg or "hand-tuned" in msg:
        parts.append(
            "The **hand-tuned CV** is the authoritative signal — it's "
            "deterministic, explainable, and has been tested on "
            "thousands of synthetic samples with 100% benchmark accuracy.\n\n"
            "The **AI classifier** is a second opinion. When both agree, "
            "confidence is very high. When they disagree, the system "
            "reports the ambiguity so you can decide — but in practice, "
            "the hand-tuned CV's verdict is the one used for the final "
            "status determination.\n\n"
            "We run both because: (1) the AI catches edge cases the "
            "hand-tuned CV might miss, and (2) the AI provides a "
            "smooth confidence score rather than a binary threshold."
        )

    else:
        # Catch-all: reply with a brief explanation
        parts.append(
            "I'm here to help you understand the verification result. "
            "You can ask me about:\n\n"
            "• The **crypto-anchor metrics** (edge sharpness, pixel bleed, "
            "block NCC, histogram)\n"
            "• The **spatial-temporal checks** (velocity, density, GPS)\n"
            "• The **AI confidence** score\n"
            "• The **supply chain** and batch information\n"
            "• The **hash chain** integrity\n"
            "• What each metric means and why it matters"
        )

    suggestions = suggestions[:5] or ["What do the crypto-anchor metrics mean?"]

    return {
        "reply": "\n\n".join(parts),
        "suggestions": suggestions,
    }


def generate_explanation(
    verify: dict,
    user_message: str | None = None,
    conversation: list[dict] | None = None,
) -> dict:
    """
    Entry point for the explain endpoint.

    First call (no conversation / empty): generates a full initial
    explanation covering all checks.
    Follow-up: generates a targeted deep-dive based on the user's
    question.
    """
    if not user_message or not user_message.strip():
        return generate_initial_explanation(verify)
    return generate_deep_dive(verify, user_message)
