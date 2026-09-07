"""Stage 1 Consistency Validation for SIF Precursor Detection.

Validates internal consistency across extracted evidence fields:
- Detects direct contradictions between extracted tokens (e.g. clearance phrases vs exposure).
- Validates alignment between energy classifier predictions and extracted hazard categories.
- CRITICAL: "No injury occurred" + direct exposure is PRESERVED as a valid near-miss.
- Contradiction detection is strictly limited to extracted facts, never inferring missing concepts.
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


def validate_consistency(
    evidence: dict[str, Any],
    energy_classification: dict[str, Any],
    activity_energy_map: Optional[dict[str, list[str]]] = None,
) -> dict[str, Any]:
    """Validate cross-field consistency on extracted tokens.
    
    Returns:
        dict with:
            - is_consistent: bool
            - warnings: list[str]
            - penalty: float (confidence deduction in [0.0, 0.4])
            - aligned_evidence: list[str]
            - is_valid_near_miss: bool
    """
    warnings: list[str] = []
    aligned: list[str] = []
    penalty = 0.0

    # -----------------------------------------------------------------------
    # 1. Exposure Contradiction Check
    # -----------------------------------------------------------------------
    # E.g. "Area was cleared of workers" co-occurring with "worker beneath load"
    exposure_data = evidence.get("exposure", {})
    if exposure_data.get("contradiction_detected", False):
        warnings.append(
            "EXPOSURE_CONTRADICTION: Report contains both explicit clearance phrasing and "
            "direct exposure markers."
        )
        penalty += 0.25

    # -----------------------------------------------------------------------
    # 2. Near-Miss Validation (Preservation Rule)
    # -----------------------------------------------------------------------
    # "No injury occurred" + direct exposure is a valid, classic near-miss
    raw_text_lower = evidence.get("raw_text", "").lower()
    has_no_injury_cue = any(
        cue in raw_text_lower
        for cue in [
            "no injury occurred", "no injury", "no personnel injured",
            "near miss", "corrected before escalation"
        ]
    )
    is_direct_exposure = exposure_data.get("label") == "direct_proximity"
    is_valid_near_miss = bool(has_no_injury_cue and is_direct_exposure)

    if is_valid_near_miss:
        aligned.append(
            "VALID_NEAR_MISS: Direct exposure with zero injury confirmed as a valid SIF near-miss precursor."
        )

    # -----------------------------------------------------------------------
    # 3. Energy Classifier vs. Hazard Evidence Alignment
    # -----------------------------------------------------------------------
    hazard_data = evidence.get("hazard", {})
    hazard_cat = hazard_data.get("best_category")
    energy_label = energy_classification.get("label")

    if hazard_cat and energy_label:
        expected_energies = HAZARD_ENERGY_ALIGNMENT.get(hazard_cat, set())
        if energy_label in expected_energies:
            aligned.append(f"ALIGNED_HAZARD_ENERGY: hazard '{hazard_cat}' aligns with energy '{energy_label}'.")
        elif expected_energies:
            warnings.append(
                f"ENERGY_HAZARD_DISAGREEMENT: Energy classifier predicted '{energy_label}', "
                f"but extracted hazard evidence indicates '{hazard_cat}'."
            )
            penalty += 0.15

    # -----------------------------------------------------------------------
    # 4. Activity vs. Energy Disagreement Check
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
    is_consistent = len(warnings) == 0

    return {
        "is_consistent": is_consistent,
        "warnings": warnings,
        "penalty": round(total_penalty, 3),
        "aligned_evidence": aligned,
        "is_valid_near_miss": is_valid_near_miss,
    }
