"""Stage 2 SCL Reasoner for SIF Precursor Detection.

Applies deterministic EEI SCL (Safety Culture & Leadership) decision logic:
- Evaluates: High-Energy Hazard + Barrier Gap + Worker Exposure
- Implements strict barrier semantics:
    * confirmed (0.0): No barrier gap.
    * uncertain (0.6): Potential barrier gap; flagged for human review.
    * explicitly_absent (1.0): Definite barrier gap.
    * not_mentioned (None): Unknown. Silence is NEVER converted into a barrier gap.
      Routes to NEEDS_MORE_INFO rather than generating a false positive.
- Generates plain-language, audit-ready justification citing exact evidence.
"""

from typing import Any, Optional


def reason(
    evidence: dict[str, Any],
    energy_classification: dict[str, Any],
    consistency_result: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Apply SCL-style decision rules to extracted evidence.
    
    Returns:
        dict with:
            - sif_potential: bool
            - lsr_tag: str
            - justification: str
            - barrier_gap: bool
            - barrier_status: str
            - barrier_gap_severity: Optional[float]
            - candidate_needs_info: bool
            - decision_factors: dict
    """
    consistency_result = consistency_result or {"is_consistent": True, "warnings": []}

    # 1. Evaluate High Energy
    is_high_energy = bool(energy_classification.get("is_high_energy", False))
    energy_label = energy_classification.get("label", "unspecified energy")
    lsr_tag_candidate = energy_classification.get("lsr_tag", "Other")

    # 2. Evaluate Barrier Gap
    barrier_data = evidence.get("barrier")
    if hasattr(barrier_data, "status"):
        barrier_status = barrier_data.status
        gap_severity = barrier_data.gap_severity
        barrier_evidence_phrases = [e.text for e in barrier_data.evidence]
    else:
        barrier_status = "not_mentioned"
        gap_severity = None
        barrier_evidence_phrases = []

    # Strict barrier gap semantics
    has_barrier_gap = False
    candidate_needs_info = False

    if barrier_status == "explicitly_absent":
        has_barrier_gap = True
    elif barrier_status == "uncertain":
        has_barrier_gap = True
    elif barrier_status == "confirmed":
        has_barrier_gap = False
    elif barrier_status == "not_mentioned":
        # Silence is NOT a barrier gap
        has_barrier_gap = False
        candidate_needs_info = True

    # 3. Evaluate Exposure
    exposure_data = evidence.get("exposure", {})
    exposure_label = exposure_data.get("label", "unspecified")
    has_exposure = exposure_label in ["direct_proximity", "indirect_proximity"]
    is_direct_exposure = exposure_label == "direct_proximity"

    # 4. SCL Core Decision
    # SIF potential requires: High Energy + Confirmed Barrier Gap + Credible Exposure
    sif_potential = bool(is_high_energy and has_barrier_gap and has_exposure)

    # LSR Tag assignment
    lsr_tag = lsr_tag_candidate if (sif_potential or candidate_needs_info) else "N/A"

    # 5. Build Audit-Ready Plain-Language Justification
    location_val = evidence.get("location", {}).get("value") or "unspecified site"
    hazard_cat = evidence.get("hazard", {}).get("best_category") or "unspecified hazard"

    justification_parts = []
    if sif_potential:
        justification_parts.append(
            f"Flagged as SIF-potential at {location_val}: {energy_label} present (hazard: '{hazard_cat}')."
        )
        if barrier_status == "explicitly_absent":
            ev_str = f" Evidence: {barrier_evidence_phrases}" if barrier_evidence_phrases else ""
            justification_parts.append(f"Critical barrier was explicitly absent (gap severity 1.0).{ev_str}")
        elif barrier_status == "uncertain":
            ev_str = f" Evidence: {barrier_evidence_phrases}" if barrier_evidence_phrases else ""
            justification_parts.append(
                f"Barrier status is uncertain/unverified (gap severity 0.6 — requires review).{ev_str}"
            )
        justification_parts.append(f"Personnel exposure confirmed ({exposure_label}).")
    elif candidate_needs_info and is_high_energy and has_exposure:
        justification_parts.append(
            f"Insufficient barrier information at {location_val}: High-energy activity ({energy_label}) with "
            f"{exposure_label} detected, but the report omitted barrier controls. Silence cannot be assumed as "
            f"barrier failure. Routed to review for verification."
        )
    else:
        reasons = []
        if not is_high_energy:
            reasons.append(f"no high-energy hazard identified ({energy_label})")
        if barrier_status == "confirmed":
            ev_str = f" ({barrier_evidence_phrases})" if barrier_evidence_phrases else ""
            reasons.append(f"barrier confirmed present{ev_str}")
        elif not has_barrier_gap and not candidate_needs_info:
            reasons.append("no barrier failure detected")
        if not has_exposure:
            reasons.append(f"no credible worker exposure ({exposure_label})")

        justification_parts.append(f"Not flagged as SIF at {location_val}: {', '.join(reasons)}.")

    # Append near-miss note if present
    if consistency_result.get("is_valid_near_miss"):
        justification_parts.append("Note: Valid SIF near-miss precursor (direct exposure with zero injury).")

    # Append any consistency warnings
    if consistency_result.get("warnings"):
        justification_parts.append(f"Consistency check: {'; '.join(consistency_result['warnings'])}.")

    justification = " ".join(justification_parts)

    return {
        "sif_potential": sif_potential,
        "lsr_tag": lsr_tag,
        "justification": justification,
        "barrier_gap": has_barrier_gap,
        "barrier_status": barrier_status,
        "barrier_gap_severity": gap_severity,
        "candidate_needs_info": candidate_needs_info,
        "decision_factors": {
            "is_high_energy": is_high_energy,
            "has_barrier_gap": has_barrier_gap,
            "has_exposure": has_exposure,
            "is_direct_exposure": is_direct_exposure,
            "gap_severity": gap_severity,
            "energy_source": energy_classification.get("source", "fallback"),
        },
    }