"""Stage 3 — evidence-strength scoring and 4-bucket review routing.

The four buckets exist because a forced binary would be dishonest about what
the system actually knows:

    HIGH_CONF_SIF      strong, mutually consistent evidence of a precursor
                       -> HSE priority review queue
    LOW_CONF_REVIEW    a genuine candidate, but with unverified or conflicting
                       evidence -> standard review queue, fields shown for fast
                       human verification
    HIGH_CONF_NON_SIF  positive evidence AGAINST a precursor (low energy, a
                       confirmed direct control, or confirmed no exposure)
                       -> logged, spot-checked at a sampling rate
    NEEDS_MORE_INFO    the report does not contain enough to decide either way
                       -> flagged back as a report-quality gap

Two design points that are easy to get wrong and matter a great deal:

1.  **Silence about a barrier is an evidence gap, not an all-clear.** When a
    high-energy report never mentions a control, the SIF verdict still stands as
    a *candidate* — absence of mention is never read as a confirmed control, or
    a real precursor at a site with sloppy reporting would be quietly filed as
    harmless and dropped out of every density statistic. But no confidence is
    claimed in either direction: the report is routed to NEEDS_MORE_INFO so a
    human closes the gap. On a low-energy report the barrier is not what decides
    the outcome, so an unrecorded one does not block a confident clear.

2.  **Confidence is evidence strength, not energy-classifier confidence.**
    Confidence in "this is a precursor" has to combine how sure we are about
    the energy, how severe the barrier gap is, and how direct the exposure is.
    Using the energy classifier's probability alone conflates "I know what kind
    of hazard this is" with "I know this is dangerous", which are different
    questions.
"""

from pathlib import Path
from typing import Any, Optional

import yaml

HIGH_CONF_SIF = "HIGH_CONF_SIF"
LOW_CONF_REVIEW = "LOW_CONF_REVIEW"
HIGH_CONF_NON_SIF = "HIGH_CONF_NON_SIF"
NEEDS_MORE_INFO = "NEEDS_MORE_INFO"

BUCKETS = [HIGH_CONF_SIF, LOW_CONF_REVIEW, HIGH_CONF_NON_SIF, NEEDS_MORE_INFO]

# Relative contribution of each SCL axis to overall evidence strength.
# Deliberately equal-ish and stated in the open rather than tuned to make the
# demo numbers look good; these are exactly the kind of weights that should be
# calibrated with OIL HSE SMEs against real review outcomes.
W_ENERGY = 0.30
W_BARRIER = 0.40
W_EXPOSURE = 0.30

_BARRIER_STRENGTH = {
    "explicitly_absent": 1.00,   # gap severity 1.0 — no control at all
    "uncertain": 0.65,           # gap severity 0.6 — present but unverified
    "not_mentioned": 0.50,       # unknown; never read as "present"
    "confirmed_present": 0.00,
    "confirmed": 0.00,
}

_EXPOSURE_STRENGTH = {
    "direct_proximity": 1.00,
    "indirect_proximity": 0.55,
    "no_exposure": 0.00,
    "unspecified": 0.35,
    "unknown": 0.35,
}


def _load_thresholds() -> dict[str, float]:
    """Load routing thresholds from configs/model_config.yaml."""
    default_thresholds = {"high_conf": 0.75, "low_conf": 0.25}
    config_path = Path(__file__).resolve().parent.parent.parent.parent / "configs" / "model_config.yaml"
    if config_path.is_file():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                return cfg.get("confidence_thresholds", default_thresholds)
        except Exception:
            pass
    return default_thresholds


def evidence_strength(
    base_confidence: float,
    decision_factors: dict[str, Any],
    barrier_status: str,
) -> float:
    """Combine the three SCL axes into a single 0-1 precursor evidence score."""
    energy_component = float(base_confidence or 0.0)
    if not decision_factors.get("is_high_energy", False):
        energy_component *= 0.25          # low energy cannot make a precursor

    barrier_component = _BARRIER_STRENGTH.get(str(barrier_status), 0.5)

    if decision_factors.get("is_direct_exposure"):
        exposure_component = _EXPOSURE_STRENGTH["direct_proximity"]
    elif decision_factors.get("has_exposure"):
        exposure_component = _EXPOSURE_STRENGTH["indirect_proximity"]
    else:
        exposure_component = _EXPOSURE_STRENGTH.get(
            str(decision_factors.get("exposure_label", "unspecified")), 0.2
        )

    score = (
        W_ENERGY * energy_component
        + W_BARRIER * barrier_component
        + W_EXPOSURE * exposure_component
    )
    return max(0.0, min(1.0, score))


def _insufficient_evidence(decision_factors: dict[str, Any], barrier_status: str) -> bool:
    """True only when NO defensible decision can be made from the report.

    Not simply "a field is missing" — an unrecorded barrier alongside a clear
    high-energy exposure still supports a precursor call.
    """
    # A confidently LOW-energy report is decidable on its own: without a
    # high-energy source there is no precursor to miss, so missing barrier or
    # exposure detail does not stop us clearing it. Treating these as
    # undecidable floods the report-quality queue with housekeeping trivia and
    # buries the reports that genuinely need a human.
    if not decision_factors.get("is_high_energy", True):
        return False

    barrier_unknown = barrier_status == "not_mentioned"
    exposure_unknown = not decision_factors.get("has_exposure") and str(
        decision_factors.get("exposure_label", "unspecified")
    ) in ("unspecified", "unknown", "")
    energy_unknown = decision_factors.get("energy_source") == "fallback"
    return bool(barrier_unknown and (exposure_unknown or energy_unknown))


# A learned classifier's own confidence below this line is too close to a
# coin flip to treat disagreement with the deterministic reasoner as a real
# signal worth escalating over - it would just add review-queue noise for
# every report the model was barely leaning on either way.
MODEL_DISAGREEMENT_THRESHOLD = 0.70


def _route_deterministic(
    sif_potential: bool,
    base_confidence: float,
    decision_factors: dict[str, Any],
    consistency_result: dict[str, Any],
    barrier_status: str,
    candidate_needs_info: bool,
) -> tuple[str, float]:
    """The SCL-only routing decision — unchanged from before model_signal existed."""
    thresholds = _load_thresholds()
    high_th = thresholds.get("high_conf", 0.75)
    low_th = thresholds.get("low_conf", 0.25)

    strength = evidence_strength(base_confidence, decision_factors, barrier_status)
    penalty = float(consistency_result.get("penalty", 0.0) or 0.0)

    is_consistent = consistency_result.get("is_consistent", True)
    has_warnings = bool(consistency_result.get("warnings"))
    contradiction = consistency_result.get("contradiction_detected", False)

    # Confidence is reported in the direction of the decision that was actually
    # made, so a confident non-SIF reads as high confidence, not low.
    confidence = strength if sif_potential else (1.0 - strength)
    confidence = round(max(0.10, min(1.0, confidence - penalty)), 3)

    is_low_energy = not decision_factors.get("is_high_energy", True)
    barrier_confirmed = barrier_status in ("confirmed_present", "confirmed")
    no_exposure = not decision_factors.get("has_exposure", True)

    # 0. An active contradiction always goes to a human, whichever way it points.
    if contradiction:
        return LOW_CONF_REVIEW, confidence

    # 1. Genuinely undecidable -> report-quality gap.
    if _insufficient_evidence(decision_factors, barrier_status):
        return NEEDS_MORE_INFO, confidence

    # 2. Barrier never described, on a HIGH-energy report -> the verdict stands
    #    as a candidate (silence is never read as a confirmed control) but we do
    #    not claim confidence in either direction; the right action is to go back
    #    and get the detail, which doubles as a report-quality signal.
    #    On a low-energy report the barrier is not what decides the outcome, so
    #    an unrecorded one is no obstacle to clearing it confidently.
    if barrier_status == "not_mentioned" and not is_low_energy:
        return NEEDS_MORE_INFO, confidence

    # 3. Precursor pathway.
    if sif_potential:
        # An *uncertain* barrier is by definition unverified evidence. It can
        # support a precursor call, but never a high-confidence one - the whole
        # point of the bucket is that a human still has to look.
        barrier_uncertain = barrier_status == "uncertain"
        if strength >= high_th and is_consistent and not has_warnings and not barrier_uncertain:
            return HIGH_CONF_SIF, confidence
        return LOW_CONF_REVIEW, confidence

    # 4. Non-precursor pathway. Requires POSITIVE evidence against, not merely
    #    the absence of evidence for. A confirmed barrier, a confirmed absence of
    #    exposure, or a low-energy activity each qualify on their own.
    strong_negative = (is_low_energy or barrier_confirmed or no_exposure)
    if strong_negative and is_consistent and barrier_status != "uncertain":
        return HIGH_CONF_NON_SIF, confidence
    if candidate_needs_info:
        return NEEDS_MORE_INFO, confidence
    return LOW_CONF_REVIEW, confidence


def route_prediction(
    sif_potential: bool,
    base_confidence: float,
    decision_factors: dict[str, Any],
    consistency_result: dict[str, Any],
    barrier_status: str,
    candidate_needs_info: bool = False,
    model_signal: Optional[dict[str, Any]] = None,
) -> tuple[str, float, dict[str, Any]]:
    """Route a prediction into one of 4 buckets.

    Returns (bucket, confidence, model_agreement). The SCL chain above — energy,
    barrier, exposure, consequence — stays the thing that decides and explains
    the verdict; it does not become a rubber stamp for whichever classifier is
    active. But it also should not silently overrule a confident, opposing read
    from the active learned model (baseline2 / mlp / the fine-tuned transformer,
    whichever ModelRegistry resolves — see inference/model_registry.py) without
    that disagreement being visible anywhere. `model_signal`, when supplied, is
    that model's own {sif_potential, confidence, model_version} for the same
    report. Two outcomes, both explicit rather than either being hidden:

    - Agreement is recorded as corroborating evidence (surfaced in the UI, not
      folded into the confidence number — the two are different kinds of
      evidence and averaging them would launder that difference away).
    - A confident disagreement (model confidence >= MODEL_DISAGREEMENT_THRESHOLD)
      demotes a would-be HIGH_CONF_* bucket to LOW_CONF_REVIEW: the same
      "an active contradiction always goes to a human" principle already
      applied to internal evidence contradictions above, extended to a
      contradiction between the deterministic chain and the learned model.
    """
    bucket, confidence = _route_deterministic(
        sif_potential=sif_potential,
        base_confidence=base_confidence,
        decision_factors=decision_factors,
        consistency_result=consistency_result,
        barrier_status=barrier_status,
        candidate_needs_info=candidate_needs_info,
    )

    model_agreement: dict[str, Any] = {
        "available": False,
        "agrees": None,
        "model_sif_potential": None,
        "model_confidence": None,
        "model_version": None,
        "escalated": False,
    }

    if model_signal and model_signal.get("sif_potential") is not None:
        model_sif = bool(model_signal["sif_potential"])
        model_conf = float(model_signal.get("confidence", 0.0) or 0.0)
        agrees = model_sif == sif_potential
        model_agreement.update(
            {
                "available": True,
                "agrees": agrees,
                "model_sif_potential": model_sif,
                "model_confidence": round(model_conf, 3),
                "model_version": model_signal.get("model_version"),
            }
        )

        confident_disagreement = (
            not agrees and model_conf >= MODEL_DISAGREEMENT_THRESHOLD
        )
        if confident_disagreement and bucket in (HIGH_CONF_SIF, HIGH_CONF_NON_SIF):
            bucket = LOW_CONF_REVIEW
            model_agreement["escalated"] = True

    return bucket, confidence, model_agreement


def route(probability: float, prediction: int) -> str:
    """Legacy 2-arg routing, kept for backward compatibility."""
    thresholds = _load_thresholds()
    high_th = thresholds.get("high_conf", 0.75)
    low_th = thresholds.get("low_conf", 0.25)

    if prediction == 1:
        return HIGH_CONF_SIF if probability >= high_th else LOW_CONF_REVIEW
    return HIGH_CONF_NON_SIF if probability >= (1.0 - low_th) else LOW_CONF_REVIEW


__all__ = [
    "route_prediction",
    "route",
    "evidence_strength",
    "HIGH_CONF_SIF",
    "LOW_CONF_REVIEW",
    "HIGH_CONF_NON_SIF",
    "NEEDS_MORE_INFO",
    "BUCKETS",
]
