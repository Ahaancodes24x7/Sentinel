"""Stage 3 Confidence Calibration & 4-Bucket Routing.

Implements the calibrated 4-bucket review routing:
- HIGH_CONF_SIF:
    * sif_potential = True
    * explicit barrier gap (explicitly_absent, severity 1.0)
    * credible worker exposure
    * good energy confidence
    * no major consistency conflict
- LOW_CONF_REVIEW:
    * SIF candidate with uncertain evidence (e.g. uncertain barrier status, severity 0.6)
    * model/rule disagreement or fallback energy classification
    * consistency warning flagged
- HIGH_CONF_NON_SIF:
    * strong positive evidence supporting non-SIF (confirmed barrier, confirmed no-exposure, or low energy)
- NEEDS_MORE_INFO:
    * critical field(s) not mentioned (e.g. barrier status omitted from report)
    * insufficient evidence to make a defensible decision
"""

from pathlib import Path
from typing import Any, Optional
import yaml


HIGH_CONF_SIF = "HIGH_CONF_SIF"
LOW_CONF_REVIEW = "LOW_CONF_REVIEW"
HIGH_CONF_NON_SIF = "HIGH_CONF_NON_SIF"
NEEDS_MORE_INFO = "NEEDS_MORE_INFO"


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


def route_prediction(
    sif_potential: bool,
    base_confidence: float,
    decision_factors: dict[str, Any],
    consistency_result: dict[str, Any],
    barrier_status: str,
    candidate_needs_info: bool = False,
) -> tuple[str, float]:
    """Route a prediction into one of 4 buckets and return (bucket_name, calibrated_confidence)."""
    thresholds = _load_thresholds()
    high_th = thresholds.get("high_conf", 0.75)
    low_th = thresholds.get("low_conf", 0.25)

    # Apply consistency penalty to calibrated confidence
    penalty = consistency_result.get("penalty", 0.0)
    calibrated_confidence = max(0.10, min(1.0, base_confidence - penalty))

    is_low_energy = not decision_factors.get("is_high_energy", True)
    barrier_confirmed = barrier_status == "confirmed"
    no_exposure = not decision_factors.get("has_exposure", True)
    is_consistent = consistency_result.get("is_consistent", True)
    has_warnings = len(consistency_result.get("warnings", [])) > 0
    energy_source = decision_factors.get("energy_source", "fallback")
    gap_severity = decision_factors.get("gap_severity")

    # -----------------------------------------------------------------------
    # 0. Active Contradiction Detection -> LOW_CONF_REVIEW
    # -----------------------------------------------------------------------
    if consistency_result.get("contradiction_detected", False):
        return LOW_CONF_REVIEW, round(calibrated_confidence, 3)

    # -----------------------------------------------------------------------
    # 1. Definite Non-SIF: Strong evidence (low energy, confirmed barrier, or no exposure)
    # -----------------------------------------------------------------------
    if not sif_potential and (is_low_energy or barrier_confirmed or no_exposure) and is_consistent and barrier_status != "uncertain":
        return HIGH_CONF_NON_SIF, round(calibrated_confidence, 3)

    # -----------------------------------------------------------------------
    # 2. NEEDS_MORE_INFO: Critical field omitted on potential high-energy candidate
    # -----------------------------------------------------------------------
    if candidate_needs_info or (decision_factors.get("is_high_energy") and barrier_status == "not_mentioned"):
        return NEEDS_MORE_INFO, round(calibrated_confidence, 3)

    # -----------------------------------------------------------------------
    # 3. SIF = True pathway
    # -----------------------------------------------------------------------
    if sif_potential:
        # High confidence SIF criteria:
        # - Explicit barrier gap (1.0)
        # - High calibrated confidence
        # - No major consistency warnings
        # - Energy classifier from model (or high confidence fallback with zero doubt)
        is_explicit_gap = barrier_status == "explicitly_absent" and gap_severity == 1.0
        no_conflict = is_consistent and not has_warnings

        if is_explicit_gap and no_conflict and calibrated_confidence >= high_th:
            return HIGH_CONF_SIF, round(calibrated_confidence, 3)
        else:
            # Uncertain barrier (0.6), fallback energy, consistency warnings, or modest confidence
            # -> Route to LOW_CONF_REVIEW
            return LOW_CONF_REVIEW, round(calibrated_confidence, 3)

    # -----------------------------------------------------------------------
    # 4. SIF = False pathway
    # -----------------------------------------------------------------------
    # Check for strong evidence supporting non-SIF:
    # e.g. barrier confirmed present, explicit no-exposure, or confirmed low energy
    if (barrier_confirmed or is_low_energy or no_exposure) and is_consistent and barrier_status != "uncertain":
        if calibrated_confidence >= low_th:
            return HIGH_CONF_NON_SIF, round(calibrated_confidence, 3)

    return LOW_CONF_REVIEW, round(calibrated_confidence, 3)



def route(probability: float, prediction: int) -> str:
    """Legacy 2-arg routing function for backward compatibility."""
    thresholds = _load_thresholds()
    high_th = thresholds.get("high_conf", 0.75)
    low_th = thresholds.get("low_conf", 0.25)

    if prediction == 1:
        return HIGH_CONF_SIF if probability >= high_th else LOW_CONF_REVIEW
    else:
        return HIGH_CONF_NON_SIF if probability >= (1.0 - low_th) else LOW_CONF_REVIEW