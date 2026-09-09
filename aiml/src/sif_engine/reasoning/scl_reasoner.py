"""Authoritative Stage 2 SCL Reasoning Engine for SIF Precursor Detection.

Applies deterministic EEI SCL (Safety Culture & Leadership) and IOGP decision rules:
- Integrates:
    * High-Energy Hazard Gating (rule/evidence-based)
    * Graded 4-State Barrier Semantics (0.0, 0.6, 1.0, None)
    * Exposure Evaluation (negation-aware)
    * Ontology-Driven Credible Consequence Assessment
    * Contradiction & Near-Miss Resolution
- Produces a fully inspectable structured reasoning object.
- Never reduces reasoning to a bare boolean; every decision includes transparent
  factors, consequence pathways, and audit-ready justifications.
"""

from typing import Any, Optional
from sif_engine.reasoning.credible_consequence import evaluate_credible_consequence


def _normalize_barrier_status(status: Optional[str]) -> str:
    """Accept legacy public labels while storing the hardened semantics internally."""
    if not status:
        return "not_mentioned"
    alias_map = {
        "confirmed_present": "confirmed_present",
        "confirmed": "confirmed_present",
        "explicitly_absent": "explicitly_absent",
        "uncertain": "uncertain",
        "not_mentioned": "not_mentioned",
        "absent_not_mentioned": "not_mentioned",
    }
    return alias_map.get(status, status)


def _legacy_barrier_label(status: Optional[str]) -> str:
    norm = _normalize_barrier_status(status)
    legacy_map = {
        "confirmed_present": "confirmed",
        "explicitly_absent": "explicitly_absent",
        "uncertain": "uncertain",
        "not_mentioned": "not_mentioned",
    }
    return legacy_map.get(norm, norm)


def _barrier_for_energy(energy_type: Optional[str]) -> str:
    """Which safety-critical barrier controls this energy type (ontology lookup)."""
    try:
        from sif_engine.data_generation.ontology import barrier_for

        return barrier_for(str(energy_type or ""))
    except Exception:
        return "Permit to work"


def _barrier_is_direct(barrier_type: str) -> bool:
    """SCL direct-control test: effective even under foreseeable human error."""
    try:
        from sif_engine.data_generation.ontology import is_direct_control

        return is_direct_control(barrier_type)
    except Exception:
        return True


def reason(
    evidence: dict[str, Any],
    energy_classification: dict[str, Any],
    consistency_result: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Apply SCL-style decision rules to extracted evidence.
    
    Returns:
        Authoritative structured reasoning dictionary.
    """
    consistency_result = consistency_result or {
        "is_consistent": True,
        "contradiction_detected": False,
        "contradiction_details": [],
        "warnings": [],
        "penalty": 0.0,
        "is_valid_near_miss": False,
    }

    # -----------------------------------------------------------------------
    # 1. High-Energy Evaluation
    # -----------------------------------------------------------------------
    is_high_energy = bool(
        energy_classification.get("high_energy_decision", energy_classification.get("is_high_energy", False))
    )
    energy_label = energy_classification.get("label", "unspecified energy")
    energy_source = energy_classification.get("high_energy_source", energy_classification.get("source", "fallback"))
    lsr_tag_candidate = energy_classification.get("lsr_tag", "Other")

    # -----------------------------------------------------------------------
    # 2. Barrier Status & Gap Severity
    # -----------------------------------------------------------------------
    barrier_data = evidence.get("barrier")
    if hasattr(barrier_data, "status"):
        barrier_status = _normalize_barrier_status(barrier_data.status)
        gap_severity = barrier_data.gap_severity
        barrier_evidence_phrases = [e.text for e in barrier_data.evidence]
    elif isinstance(barrier_data, dict):
        barrier_status = _normalize_barrier_status(barrier_data.get("status", "not_mentioned"))
        gap_severity = barrier_data.get("gap_severity")
        barrier_evidence_phrases = [barrier_data.get("text", "")] if barrier_data.get("text") else []
    else:
        barrier_status = "not_mentioned"
        gap_severity = None
        barrier_evidence_phrases = []

    # Explicit 4-State Barrier Decision Logic
    has_barrier_gap = False
    candidate_needs_info = False

    if barrier_status == "explicitly_absent":
        has_barrier_gap = True
    elif barrier_status == "uncertain":
        has_barrier_gap = True
    elif barrier_status == "confirmed_present":
        has_barrier_gap = False
    elif barrier_status == "not_mentioned":
        # Absence of mention is NOT evidence of presence. Reading an unrecorded
        # barrier as a confirmed one is exactly how a live precursor gets filed
        # as harmless, and it is the failure mode the SCL model and the research
        # blueprint both single out. So this counts as an (unconfirmed) gap for
        # the SIF decision, while ALSO raising the needs-more-info flag so the
        # report is routed to a human to close the evidence gap rather than the
        # model quietly guessing either way.
        has_barrier_gap = True
        candidate_needs_info = True

    # -----------------------------------------------------------------------
    # 3. Exposure Evaluation
    # -----------------------------------------------------------------------
    exposure_data = evidence.get("exposure", {})
    exposure_label = exposure_data.get("label", "unspecified")
    textual_exposure = (evidence.get("raw_text") or "").lower()
    explicit_exposure = any(phrase in textual_exposure for phrase in [
        "worker was exposed", "worker was exposed to", "personnel were exposed",
        "exposed to an energized electrical component", "exposed to electrical energy",
        "was exposed to", "worker exposed to"
    ])
    if exposure_label == "unspecified" and explicit_exposure:
        exposure_label = "direct_proximity"
    has_exposure = exposure_label in ["direct_proximity", "indirect_proximity"]
    is_direct_exposure = exposure_label == "direct_proximity"

    # -----------------------------------------------------------------------
    # 4. Credible Consequence Modeling
    # -----------------------------------------------------------------------
    hazard_info = evidence.get("hazard", {})
    best_hazard = hazard_info.get("best_category") if isinstance(hazard_info, dict) else None

    consequence_info = evaluate_credible_consequence(
        energy_type=energy_label,
        hazard_category=best_hazard,
        exposure_label=exposure_label,
    )

    # -----------------------------------------------------------------------
    # 5. SCL Core Decision
    # -----------------------------------------------------------------------
    is_valid_near_miss = consistency_result.get("is_valid_near_miss", False)
    sif_potential = bool(
        (is_high_energy and has_barrier_gap and has_exposure) or
        (is_valid_near_miss and is_high_energy and is_direct_exposure and barrier_status != "confirmed_present")
    )

    # SCL "direct control" test. A control counts as clearing the exposure only
    # if it remains effective under foreseeable human error - a mechanical or
    # engineering barrier. A confirmed ADMINISTRATIVE control (a permit, a
    # journey management plan) does not clear a high-energy exposure the way an
    # engineering one does, so a confirmed permit alone must not zero out the
    # SIF decision.
    controlling_barrier = _barrier_for_energy(energy_label)
    barrier_is_direct = _barrier_is_direct(controlling_barrier)
    if barrier_status == "confirmed_present":
        sif_potential = bool(
            is_high_energy and has_exposure and not barrier_is_direct
        )

    if sif_potential or candidate_needs_info:
        lsr_tag = consequence_info.get("lsr_tag") or lsr_tag_candidate
        if lsr_tag in ["Other", "N/A"]:
            lsr_tag = lsr_tag_candidate
    else:
        lsr_tag = "N/A"

    # -----------------------------------------------------------------------
    # 6. Build Audit-Ready Plain-Language Justification
    # -----------------------------------------------------------------------
    location_val = evidence.get("location", {}).get("value") or "unspecified site"
    hazard_cat = best_hazard or "unspecified hazard"

    justification_parts = []
    if sif_potential:
        justification_parts.append(
            f"Flagged as SIF Precursor at {location_val}: High-energy hazard identified ({energy_label}, hazard category: '{hazard_cat}')."
        )
        if barrier_status == "explicitly_absent":
            ev_str = f" (evidence: {barrier_evidence_phrases})" if barrier_evidence_phrases else ""
            justification_parts.append(f"Critical barrier was explicitly absent (gap severity: 1.0).{ev_str}")
        elif barrier_status == "uncertain":
            ev_str = f" (evidence: {barrier_evidence_phrases})" if barrier_evidence_phrases else ""
            justification_parts.append(
                f"Barrier status is uncertain or unverified (gap severity: 0.6 — requires supervisor review).{ev_str}"
            )
        elif barrier_status == "not_mentioned":
            # State the evidence gap explicitly. The reviewer needs to know the
            # flag rests on an ABSENT record rather than on observed failure -
            # that is the difference between "go and verify the isolation" and
            # "the isolation failed", and it is also what tells the reporting
            # team their form is missing a field people skip.
            justification_parts.append(
                "Report omitted barrier controls entirely: no control was confirmed, so the "
                "exposure is unmitigated on the available evidence. Absence of mention is not "
                "read as a confirmed barrier — barrier verification required."
            )
        justification_parts.append(f"Personnel exposure confirmed ({exposure_label}).")
        justification_parts.append(f"Credible consequence: {consequence_info.get('primary_consequence')}.")
    elif candidate_needs_info and is_high_energy and has_exposure:
        justification_parts.append(
            f"Insufficient barrier information at {location_val}: High-energy activity ({energy_label}) with "
            f"{exposure_label} detected, but report omitted barrier controls. Silence cannot be assumed as "
            f"barrier failure. Routed to review for barrier verification."
        )
    else:
        reasons = []
        if not is_high_energy:
            reasons.append(f"no high-energy hazard identified ({energy_label})")
        if barrier_status == "confirmed_present":
            ev_str = f" ({barrier_evidence_phrases})" if barrier_evidence_phrases else ""
            reasons.append(f"barrier confirmed present{ev_str}")
        elif not has_barrier_gap and not candidate_needs_info:
            reasons.append("no barrier failure detected")
        if not has_exposure:
            reasons.append(f"no credible worker exposure ({exposure_label})")

        justification_parts.append(f"Not flagged as SIF at {location_val}: {', '.join(reasons)}.")

    if is_valid_near_miss:
        justification_parts.append("Note: Valid SIF near-miss precursor preserved (direct exposure with zero injury).")

    if consistency_result.get("contradiction_detected"):
        for c in consistency_result.get("contradiction_details", []):
            justification_parts.append(f"Contradiction flagged: {c.get('message')}")
    elif consistency_result.get("warnings"):
        justification_parts.append(f"Consistency notes: {'; '.join(consistency_result['warnings'])}.")

    justification = " ".join(justification_parts)

    decision_factors = {
        "is_high_energy": is_high_energy,
        "has_barrier_gap": has_barrier_gap,
        "has_exposure": has_exposure,
        "is_direct_exposure": is_direct_exposure,
        "exposure_label": exposure_label,
        "gap_severity": gap_severity,
        "barrier_status": barrier_status,
        "energy_source": energy_source,
        "is_valid_near_miss": is_valid_near_miss,
        "consequence_severity": consequence_info.get("potential_severity"),
        "contradiction_detected": consistency_result.get("contradiction_detected", False),
    }

    missing_information = []
    if barrier_status == "not_mentioned":
        missing_information.append("barrier not described")
    if exposure_label in {"unspecified", "unknown"}:
        missing_information.append("exposure proximity unclear")
    if is_high_energy and not (best_hazard or energy_label):
        missing_information.append("energy pathway ambiguous")
    if not evidence.get("location", {}).get("value"):
        missing_information.append("location unresolved")

    contradictions = [
        {
            "type": item.get("type", "consistency_issue"),
            "evidence_a": item.get("conflicting_fields", ["unknown", "unknown"])[0],
            "evidence_b": item.get("conflicting_fields", ["unknown", "unknown"])[1] if len(item.get("conflicting_fields", ["unknown", "unknown"])) > 1 else "unknown",
            "severity": "high" if item.get("penalty", 0) >= 0.2 else "medium",
            "message": item.get("message", "Consistency issue detected"),
        }
        for item in consistency_result.get("contradiction_details", [])
    ]

    evidence_items = []
    for item in evidence.get("evidence_spans", []):
        evidence_items.append({
            "field": item.get("field"),
            "text": item.get("text"),
            "span": item.get("span"),
            "confidence": item.get("confidence", 0.8),
        })
    if not evidence_items:
        for field_name in ["activity", "hazard", "exposure", "barrier", "location"]:
            nested = evidence.get(field_name)
            if isinstance(nested, dict):
                if nested.get("span") and nested.get("text"):
                    evidence_items.append({
                        "field": field_name,
                        "text": nested.get("text"),
                        "span": nested.get("span"),
                        "confidence": nested.get("confidence", 0.8),
                    })

    reasoning_steps = [
        {"step": 1, "label": "Activity", "detail": f"Identified activity: {evidence.get('activity', {}).get('text', 'unspecified activity')}"},
        {"step": 2, "label": "Hazard/Energy", "detail": f"Energy signal: {energy_label}; hazard evidence: {best_hazard or 'not explicitly identified'}"},
        {"step": 3, "label": "Exposure", "detail": f"Exposure mode: {exposure_label}"},
        {"step": 4, "label": "Barrier", "detail": f"Barrier status: {barrier_status}; gap severity: {gap_severity}"},
        {"step": 5, "label": "Credible consequence", "detail": consequence_info.get("primary_consequence", "No explicit consequence mapped")},
        {"step": 6, "label": "SIF potential", "detail": "SIF potential likely" if sif_potential else "No SIF pathway under current evidence"},
        {"step": 7, "label": "LSR", "detail": f"LSR mapping: {lsr_tag or 'unresolved'}"},
    ]

    lsr_payload = {
        "rule": lsr_tag if lsr_tag and lsr_tag not in ["N/A", "Other"] else "unresolved",
        "reason": consequence_info.get("description", "No ontology rule matched the current evidence."),
        "confidence": 0.5,
        "ontology_source": "rule_engine",
    }
    if lsr_tag not in [None, "N/A", "Other"]:
        lsr_payload["confidence"] = 0.9 if barrier_status == "explicitly_absent" else 0.75 if barrier_status == "uncertain" else 0.85 if barrier_status == "confirmed_present" else 0.7
    if not is_high_energy:
        lsr_payload["rule"] = "unresolved"
        lsr_payload["confidence"] = 0.0

    structured_reasoning = {
        "activity": evidence.get("activity", {}),
        "hazard": evidence.get("hazard", {}),
        "energy": {
            "label": energy_label,
            "is_high_energy": is_high_energy,
            "source": energy_source,
            "confidence": energy_classification.get("confidence", 0.7),
            "high_energy_confidence": energy_classification.get("high_energy_confidence", 0.7),
            "high_energy_evidence": energy_classification.get("high_energy_evidence", []),
        },
        "exposure": exposure_data,
        "barrier": {
            "status": barrier_status,
            "gap_severity": gap_severity,
            "evidence": barrier_evidence_phrases,
            "legacy_label": _legacy_barrier_label(barrier_status),
        },
        "environment": evidence.get("environment", {}),
        "credible_consequence": consequence_info,
        "sif_potential": sif_potential,
        "lsr": lsr_payload,
        "missing_information": missing_information,
        "contradictions": contradictions,
        "evidence": evidence_items,
        "reasoning_steps": reasoning_steps,
        "provenance": {
            "energy_source": energy_source,
            "barrier_source": "raw_text_evidence",
            "model_version": energy_classification.get("model_version", "rule-fallback-v0.1"),
            "ontology_version": "sif_ontology_v1",
            "source": "structured_reasoning_engine",
        },
        "sif_potential_legacy": sif_potential,
        "lsr_tag": lsr_tag,
        "justification": justification,
        "barrier_gap": has_barrier_gap,
        "barrier_status": _legacy_barrier_label(barrier_status),
        "barrier_gap_severity": gap_severity,
        "candidate_needs_info": candidate_needs_info,
        "credible_consequence_legacy": consequence_info,
        "contradictions_detected": contradictions,
        "decision_factors": decision_factors,
    }

    structured_reasoning.update({
        "sif_potential": sif_potential,
        "lsr_tag": lsr_tag,
        "justification": justification,
        "barrier_gap": has_barrier_gap,
        "barrier_status": _legacy_barrier_label(barrier_status),
        "barrier_gap_severity": gap_severity,
        "candidate_needs_info": candidate_needs_info,
        "credible_consequence": consequence_info,
        "contradictions_detected": contradictions,
        "decision_factors": decision_factors,
    })

    return structured_reasoning