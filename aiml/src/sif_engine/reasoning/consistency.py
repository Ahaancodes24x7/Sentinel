"""Stage 1 & Stage 2 Consistency & Contradiction Resolution Engine for SIF Detection.

Validates internal consistency across extracted evidence fields:
- Detects factual contradictions:
    1. Exposure clearance vs direct exposure (e.g. "area cleared of all workers" vs "worker directly under crane arm")
    2. Energy isolation claimed confirmed vs energized/live equipment exposed
    3. Energy classifier prediction vs extracted hazard evidence disagreement
- CRITICAL PRESERVATION RULE: "No injury occurred" + direct high-energy exposure
  is PRESERVED as a valid SIF near-miss precursor. It is NEVER flagged as a contradiction.
- Silence on barriers routes to NEEDS_MORE_INFO, never assumed to be barrier failure.
- When contradictions occur, provides structured details and applies calibrated penalties.
"""

from typing import Any, Optional

# ---------------------------------------------------------------------------
# Canonical Hazard <-> Energy Alignment Map
# ---------------------------------------------------------------------------
HAZARD_ENERGY_ALIGNMENT: dict[str, set[str]] = {
    "energy_isolation": {"stored/electrical energy"},
    "hot_work": {"thermal (hot work)", "stored/electrical energy"},
    "confined_space": {"atmospheric/asphyxiation"},
    "line_of_fire": {"kinetic (line of fire)", "gravitational (suspended load)"},
    "safe_mechanical_lifting": {"gravitational (suspended load)", "kinetic (line of fire)"},
    "working_at_height": {"fall from height", "gravitational (suspended load)"},
    "driving": {"vehicular/motion"},
    "excavation": {"stored/electrical energy", "kinetic (line of fire)"},
}


def _is_high_energy(energy_type) -> bool:
    """Ontology lookup, tolerant of the hazard-category vocabulary."""
    if not energy_type:
        return False
    try:
        from sif_engine.data_generation.ontology import ENERGY_TYPES, high_energy

        if energy_type in ENERGY_TYPES:
            return high_energy(energy_type)
        # hazard categories such as "energy_isolation" map through the LSR table
        from sif_engine.extraction.energy_classifier import HAZARD_TO_ENERGY_MAP

        mapped = HAZARD_TO_ENERGY_MAP.get(str(energy_type))
        return high_energy(mapped) if mapped else False
    except Exception:
        return False


def validate_consistency(
    evidence: dict[str, Any],
    energy_classification: dict[str, Any],
    activity_energy_map: Optional[dict[str, list[str]]] = None,
) -> dict[str, Any]:
    """Validate cross-field consistency on extracted tokens and detect contradictions.
    
    Returns:
        dict with:
            - is_consistent: bool
            - contradiction_detected: bool
            - contradiction_details: list[dict]
            - warnings: list[str]
            - penalty: float (confidence deduction in [0.0, 0.4])
            - aligned_evidence: list[str]
            - is_valid_near_miss: bool
            - requires_human_review: bool
    """
    warnings: list[str] = []
    aligned: list[str] = []
    contradiction_details: list[dict[str, Any]] = []
    penalty = 0.0

    raw_text = evidence.get("raw_text", "")
    raw_text_lower = raw_text.lower()

    # -----------------------------------------------------------------------
    # 1. Exposure Contradiction Check
    # -----------------------------------------------------------------------
    # E.g. "Area was cleared of all workers" co-occurring with "worker directly under crane arm"
    exposure_data = evidence.get("exposure", {})
    exposure_label = exposure_data.get("label", "unspecified")

    # Check explicit presence of both clearance phrases and direct exposure phrases
    has_clearance_cue = any(
        cue in raw_text_lower
        for cue in [
            "area was clear of workers", "area was cleared of workers",
            "area was clear of all personnel", "area was cleared of all workers",
            "area was cleared of all personnel", "barricaded with no entry",
            "no personnel were in the vicinity", "no workers were present"
        ]
    )
    has_direct_worker_cue = any(
        cue in raw_text_lower
        for cue in [
            "directly under", "directly beneath", "worker beneath",
            "worker directly under", "under crane arm", "inside the equipment",
            "worker entered", "personnel entered", "entered the vessel",
            "in the line of fire", "worker below"
        ]
    )

    if (exposure_data.get("contradiction_detected", False)) or (has_clearance_cue and has_direct_worker_cue):
        detail = {
            "type": "EXPOSURE_CONTRADICTION",
            "message": "EXPOSURE_CONTRADICTION: Report contains both explicit clearance phrasing and direct personnel exposure markers.",
            "conflicting_fields": ["exposure.clearance", "exposure.direct_proximity"],
            "penalty": 0.25,
        }
        contradiction_details.append(detail)
        warnings.append(detail["message"])
        penalty += 0.25

    # -----------------------------------------------------------------------
    # 2. Barrier Isolation vs. Energized Conflict
    # -----------------------------------------------------------------------
    # E.g. "LOTO confirmed" but report mentions "working on live / energized circuit"
    barrier_data = evidence.get("barrier")
    barrier_status = getattr(barrier_data, "status", "not_mentioned") if barrier_data else "not_mentioned"
    has_live_hazard = any(
        cue in raw_text_lower
        for cue in ["live circuit", "energized", "live wire", "arc flash", "live switchboard"]
    )
    if barrier_status == "confirmed" and has_live_hazard:
        detail = {
            "type": "BARRIER_HAZARD_CONTRADICTION",
            "message": "BARRIER_HAZARD_CONTRADICTION: Barrier reported as confirmed/isolated while report indicates working directly on live/energized equipment.",
            "conflicting_fields": ["barrier_status.confirmed", "hazard.energized"],
            "penalty": 0.20,
        }
        contradiction_details.append(detail)
        warnings.append(detail["message"])
        penalty += 0.20

    # -----------------------------------------------------------------------
    # 3. Near-Miss Validation (Preservation Rule)
    # -----------------------------------------------------------------------
    # "No injury occurred" + direct exposure is a valid, classic SIF near-miss precursor.
    # MUST NOT be treated as a contradiction.
    has_no_injury_cue = any(
        cue in raw_text_lower
        for cue in [
            "no injury occurred", "no injury", "no personnel injured",
            "zero injury", "near miss", "corrected before escalation",
            "deflected by netting", "worker ducked", "narrowly avoided"
        ]
    )
    is_direct_exposure = exposure_label in ["direct_proximity", "indirect_proximity"] or has_direct_worker_cue
    is_valid_near_miss = bool(has_no_injury_cue and is_direct_exposure)

    if is_valid_near_miss:
        aligned.append(
            "VALID_NEAR_MISS: Direct hazard exposure with zero injury confirmed as a valid SIF near-miss precursor."
        )

    # -----------------------------------------------------------------------
    # 4. Energy Classifier vs. Hazard Evidence Alignment
    # -----------------------------------------------------------------------
    hazard_data = evidence.get("hazard", {})
    hazard_cat = hazard_data.get("best_category")
    energy_label = energy_classification.get("label")

    if hazard_cat and energy_label:
        expected_energies = HAZARD_ENERGY_ALIGNMENT.get(hazard_cat, set())
        if energy_label in expected_energies:
            aligned.append(f"ALIGNED_HAZARD_ENERGY: hazard '{hazard_cat}' aligns with energy '{energy_label}'.")
        elif expected_energies:
            message = (
                f"ENERGY_HAZARD_DISAGREEMENT: Energy classifier predicted "
                f"'{energy_label}', but extracted hazard evidence indicates '{hazard_cat}'."
            )
            # A disagreement about WHICH high-energy type is present does not
            # undermine the SIF decision - that decision turns on high-energy
            # yes/no, barrier state and exposure, all of which are unaffected.
            # Treating it as a hard contradiction sent genuinely decidable
            # reports to the ambiguity queue and masked the barrier-silence
            # signal underneath. It stays a warning with a confidence penalty;
            # only a disagreement that crosses the high/low energy boundary is
            # a real contradiction, because that one does flip the verdict.
            both_high_energy = _is_high_energy(energy_label) and any(
                _is_high_energy(candidate) for candidate in expected_energies
            )
            detail = {
                "type": "ENERGY_HAZARD_DISAGREEMENT",
                "message": message,
                "conflicting_fields": ["energy_classification.label", "hazard.best_category"],
                "penalty": 0.15,
            }
            warnings.append(message)
            penalty += 0.15
            if not both_high_energy:
                contradiction_details.append(detail)


    # -----------------------------------------------------------------------
    # 5. Activity vs. Energy Disagreement Check
    # -----------------------------------------------------------------------
    if activity_energy_map:
        activity_data = evidence.get("activity", {})
        activity_text = activity_data.get("category") or activity_data.get("text", "")
        plausible_energies = activity_energy_map.get(activity_text)
        if plausible_energies and energy_label and energy_label not in plausible_energies:
            warnings.append(
                f"ACTIVITY_ENERGY_MISMATCH: Energy '{energy_label}' is atypical for activity '{activity_text}'."
            )
            penalty += 0.10

    # Cap total penalty at 0.40
    total_penalty = min(penalty, 0.40)
    contradiction_detected = len(contradiction_details) > 0
    is_consistent = not contradiction_detected and len(warnings) == 0

    return {
        "is_consistent": is_consistent,
        "contradiction_detected": contradiction_detected,
        "contradiction_details": contradiction_details,
        "warnings": warnings,
        "penalty": round(total_penalty, 3),
        "aligned_evidence": aligned,
        "is_valid_near_miss": is_valid_near_miss,
        "requires_human_review": contradiction_detected,
    }
