"""
PS 26165 / Sentinel — scl_reasoner.py — THE FINALIZED Stage 2 reasoning engine.

This replaces every prior ad-hoc scl_reason()/scl_reason_v2/scl_reason_v3_final
experiment with one production module, built from the ablation's actual
measured conclusions (stage1_energy_scl_ablation.py), not from assumption:

  - HIGH-ENERGY GATE: rule-based hazard-evidence extractor (Experiment D).
    Measured best F2 (0.781) among non-diagnostic options, BEATING both the
    current multiclass-derived gate (0.744) and a dedicated binary
    classifier (0.687) — despite having the lowest raw accuracy (0.751) of
    the three. Chosen for its recall-favoring error asymmetry, which is
    what this project has committed to prioritizing, not for raw accuracy.

  - BARRIER STATUS: 4-state graded assessment (confirmed / uncertain /
    explicitly_absent / not_mentioned), never collapsed to a boolean.
    not_mentioned routes to NEEDS_MORE_INFO — silence is never treated as
    an assumed failure.

  - EXPOSURE: negation-aware ("no personnel were in the vicinity" is
    correctly NOT indirect exposure).

  - energy_type (multiclass, if supplied): kept as an INFORMATIONAL /
    LSR-naming field only. It is never used for the high-energy gate
    decision — that was tried (Experiment C's derived/dedicated variants)
    and did not outperform the rule-based gate.

Every field in the output is named and traceable to evidence with real
character offsets into the ORIGINAL raw text (not the preprocessed
string) — this is deliberate: evidence spans must point at what a human
reviewer can actually go read, and preprocessing (abbreviation expansion,
typo correction) shifts character positions relative to the raw input.

Provenance is explicit: every result states which component produced the
high-energy signal (`hazard_gate_source`), so a rule-based fallback can
never silently masquerade as a trained-model prediction.
"""

from dataclasses import dataclass, field
from evidence_extractor import extract_evidence, extract_category_evidence, HAZARD_KEYWORD_GROUPS

ENERGY_CATEGORY_TO_LSR = {
    "energy_isolation": "Energy Isolation",
    "hot_work": "Hot Work",
    "confined_space": "Confined Space",
    "line_of_fire": "Line of Fire",
    "safe_mechanical_lifting": "Safe Mechanical Lifting",
    "working_at_height": "Working at Height",
    "driving": "Driving",
    "excavation": "N/A",  # excavation keyword alone is ambiguous re: high-energy (see ablation finding)
}

VALID_BUCKETS = {"HIGH_CONF_SIF", "LOW_CONF_REVIEW", "HIGH_CONF_NON_SIF", "NEEDS_MORE_INFO"}


@dataclass
class ReasoningResult:
    sif_potential: bool | None       # True / False / None (None = genuinely undetermined)
    bucket: str                      # one of VALID_BUCKETS
    lsr_tag: str
    justification: str
    confidence_note: str
    hazard_category: str | None
    hazard_gate_source: str          # provenance — never silently ambiguous
    barrier_status: str
    barrier_gap_severity: float
    exposure_category: str | None
    location: str | None
    evidence: dict = field(default_factory=dict)   # raw evidence spans, for UI highlighting


def _is_high_energy_rule_based(raw_text: str) -> tuple[bool, str | None]:
    """Experiment D's gate — the measured winner. Returns
    (is_high_energy, matched_hazard_category)."""
    result = extract_category_evidence(raw_text, HAZARD_KEYWORD_GROUPS)
    return result["best_category"] is not None, result["best_category"]


def reason(raw_text: str, predicted_energy_type: str | None = None) -> ReasoningResult:
    """The single public entry point for Stage 2.

    Args:
        raw_text: the ORIGINAL, unprocessed report text (evidence spans are
            computed against this, not the Stage-0-preprocessed version).
        predicted_energy_type: optional multiclass energy_type prediction
            from the Stage 1 classifier — used ONLY for LSR-tag naming
            when it is more specific than the rule-based hazard category
            (informational), NEVER for the high-energy gate decision.

    Returns:
        A ReasoningResult with a tri-state sif_potential, a bucket
        assignment, evidence, and full provenance.
    """
    ev = extract_evidence(raw_text)
    is_high_energy, hazard_category = _is_high_energy_rule_based(raw_text)
    hazard_gate_source = "rule_based_evidence_extractor_v1"  # explicit provenance, always stated

    barrier = ev["barrier"]
    exposure_category = ev["exposure"]["best_category"]
    has_exposure = exposure_category is not None and exposure_category != "no_exposure"
    location = ev["location"]["value"]

    # --- The tri-state decision, per the ablation's corrected semantics ---
    if barrier.status == "not_mentioned":
        sif_potential = None
        bucket = "NEEDS_MORE_INFO"
        confidence_note = "Insufficient barrier information in report — cannot confirm or rule out a gap."
    else:
        barrier_gap = barrier.status in ("uncertain", "explicitly_absent")
        sif_potential = bool(is_high_energy and barrier_gap and has_exposure)
        if not sif_potential:
            bucket = "HIGH_CONF_NON_SIF"
            confidence_note = "N/A"
        elif barrier.status == "explicitly_absent":
            bucket = "HIGH_CONF_SIF"
            confidence_note = "HIGH confidence — explicit evidence of barrier absence."
        else:  # uncertain
            bucket = "LOW_CONF_REVIEW"
            confidence_note = "MEDIUM confidence — uncertain barrier language, recommend human review."

    assert bucket in VALID_BUCKETS, f"invalid bucket produced: {bucket}"

    # LSR tag: prefer the specific multiclass prediction if it maps cleanly
    # and agrees with the rule-based category being present at all;
    # otherwise fall back to the rule-based hazard category. Never invent
    # a tag when sif_potential is not True.
    if sif_potential:
        lsr_tag = ENERGY_CATEGORY_TO_LSR.get(hazard_category, "N/A")
        if lsr_tag == "N/A" and predicted_energy_type:
            # informational fallback naming only — does not affect sif_potential
            lsr_tag = {
                "stored/electrical energy": "Energy Isolation", "thermal (hot work)": "Hot Work",
                "gravitational (suspended load)": "Safe Mechanical Lifting", "kinetic (line of fire)": "Line of Fire",
                "atmospheric/asphyxiation": "Confined Space", "vehicular/motion": "Driving",
                "fall from height": "Working at Height",
            }.get(predicted_energy_type, "N/A")
    else:
        lsr_tag = "N/A"

    loc_str = location or "unspecified location"
    barrier_evidence_phrases = [e.phrase for e in barrier.evidence]
    if sif_potential is True:
        justification = (
            f"Flagged as SIF-potential at {loc_str}: hazard category '{hazard_category}' "
            f"(source: {hazard_gate_source}), barrier status '{barrier.status}' "
            f"(gap severity {barrier.gap_severity:.1f}, evidence: {barrier_evidence_phrases or 'none'}), "
            f"exposure '{exposure_category}'."
        )
    elif sif_potential is False:
        reasons = []
        if not is_high_energy:
            reasons.append("no high-energy hazard evidence found")
        if barrier.status not in ("uncertain", "explicitly_absent"):
            reasons.append(f"barrier status '{barrier.status}' (evidence: {barrier_evidence_phrases or 'none'})")
        if not has_exposure:
            reasons.append(f"no credible exposure (category: {exposure_category})")
        justification = f"Not flagged at {loc_str}: {', '.join(reasons)}."
    else:
        justification = (
            f"Cannot determine SIF-potential at {loc_str}: report does not state barrier/control status "
            f"one way or the other. Hazard category: '{hazard_category}', exposure: '{exposure_category}'. "
            "Routed for human review to supply the missing information — NOT assumed to be a barrier failure."
        )

    return ReasoningResult(
        sif_potential=sif_potential, bucket=bucket, lsr_tag=lsr_tag, justification=justification,
        confidence_note=confidence_note, hazard_category=hazard_category, hazard_gate_source=hazard_gate_source,
        barrier_status=barrier.status, barrier_gap_severity=barrier.gap_severity,
        exposure_category=exposure_category, location=location, evidence=ev,
    )


if __name__ == "__main__":
    samples = [
        "During maintenance on process equipment at Rig 4, a worker was standing within the immediate hazard zone. Isolation status was not clearly confirmed by the crew. No injury occurred.",
        "During electrical panel work at Well Site B, a technician was inside the equipment when work commenced. No isolation was mentioned in the report. Minor first aid case reported.",
        "During routine equipment inspection at Plant C, isolation was verified and tagged before work began. No personnel were in the vicinity at the time. No injury occurred.",
        "Routine patrol at Terminal A. No personnel were in the vicinity. No injury occurred.",
    ]
    for text in samples:
        r = reason(text)
        print(f"TEXT: {text}")
        print(f"  -> sif_potential={r.sif_potential}  bucket={r.bucket}  lsr_tag={r.lsr_tag}")
        print(f"  -> {r.justification}")
        print(f"  -> confidence: {r.confidence_note}")
        print()
