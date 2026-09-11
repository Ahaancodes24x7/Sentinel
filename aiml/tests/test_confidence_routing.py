"""Stage 3 confidence & routing tests.

Covers the 4-bucket routing logic in isolation (no model loading — every case
below passes `model_signal` as a plain dict, so these pass on a fresh clone
without the gitignored transformer checkpoint present) and the model-vs-SCL
cross-check added to `route_prediction`: a confident disagreement between the
deterministic SCL reasoner and the active learned classifier must not be
silently discarded.
"""

import pytest

from sif_engine.confidence.routing import (
    HIGH_CONF_NON_SIF,
    HIGH_CONF_SIF,
    LOW_CONF_REVIEW,
    NEEDS_MORE_INFO,
    route_prediction,
)

HIGH_ENERGY_FACTORS = {"is_high_energy": True, "is_direct_exposure": True, "has_exposure": True}
CONSISTENT = {"is_consistent": True, "warnings": [], "contradiction_detected": False, "penalty": 0.0}


def test_high_energy_direct_exposure_absent_barrier_is_high_conf_sif():
    """Sanity baseline: no model_signal at all still behaves exactly as before."""
    bucket, confidence, agreement = route_prediction(
        sif_potential=True,
        base_confidence=0.9,
        decision_factors=HIGH_ENERGY_FACTORS,
        consistency_result=CONSISTENT,
        barrier_status="explicitly_absent",
    )
    assert bucket == HIGH_CONF_SIF
    assert confidence > 0.75
    assert agreement == {
        "available": False,
        "agrees": None,
        "model_sif_potential": None,
        "model_confidence": None,
        "model_version": None,
        "escalated": False,
    }


def test_model_agreement_is_recorded_but_does_not_change_a_high_conf_sif_bucket():
    bucket, _confidence, agreement = route_prediction(
        sif_potential=True,
        base_confidence=0.9,
        decision_factors=HIGH_ENERGY_FACTORS,
        consistency_result=CONSISTENT,
        barrier_status="explicitly_absent",
        model_signal={"sif_potential": True, "confidence": 0.95, "model_version": "test-model"},
    )
    assert bucket == HIGH_CONF_SIF
    assert agreement["available"] is True
    assert agreement["agrees"] is True
    assert agreement["escalated"] is False


def test_confident_model_disagreement_demotes_high_conf_sif_to_review():
    """The case that matters: SCL says a confident precursor, the model confidently
    disagrees — the disagreement must be visible, not silently overruled either way."""
    bucket, _confidence, agreement = route_prediction(
        sif_potential=True,
        base_confidence=0.9,
        decision_factors=HIGH_ENERGY_FACTORS,
        consistency_result=CONSISTENT,
        barrier_status="explicitly_absent",
        model_signal={"sif_potential": False, "confidence": 0.92, "model_version": "test-model"},
    )
    assert bucket == LOW_CONF_REVIEW
    assert agreement["agrees"] is False
    assert agreement["escalated"] is True


def test_confident_model_disagreement_demotes_high_conf_non_sif_to_review():
    """Same rule in the other direction: a confident 'clear' should not survive a
    confident model objection either — disagreement isn't allowed to only cut one way."""
    bucket, _confidence, agreement = route_prediction(
        sif_potential=False,
        base_confidence=0.9,
        decision_factors={"is_high_energy": False, "has_exposure": False},
        consistency_result=CONSISTENT,
        barrier_status="confirmed_present",
        model_signal={"sif_potential": True, "confidence": 0.88, "model_version": "test-model"},
    )
    assert bucket == LOW_CONF_REVIEW
    assert agreement["escalated"] is True


def test_weak_model_disagreement_does_not_escalate():
    """A model barely leaning the other way (below MODEL_DISAGREEMENT_THRESHOLD) is
    noise, not a real second opinion — escalating on it would just flood the review
    queue with reports the model itself was unsure about."""
    bucket, _confidence, agreement = route_prediction(
        sif_potential=True,
        base_confidence=0.9,
        decision_factors=HIGH_ENERGY_FACTORS,
        consistency_result=CONSISTENT,
        barrier_status="explicitly_absent",
        model_signal={"sif_potential": False, "confidence": 0.55, "model_version": "test-model"},
    )
    assert bucket == HIGH_CONF_SIF
    assert agreement["agrees"] is False
    assert agreement["escalated"] is False


def test_model_disagreement_never_downgrades_an_already_human_reviewed_bucket():
    """LOW_CONF_REVIEW and NEEDS_MORE_INFO already go to a human; disagreement has
    nothing further to escalate there, and must not be reported as if it did."""
    bucket, _confidence, agreement = route_prediction(
        sif_potential=True,
        base_confidence=0.9,
        decision_factors=HIGH_ENERGY_FACTORS,
        consistency_result=CONSISTENT,
        barrier_status="uncertain",  # forces LOW_CONF_REVIEW even though sif_potential=True
        model_signal={"sif_potential": False, "confidence": 0.95, "model_version": "test-model"},
    )
    assert bucket == LOW_CONF_REVIEW
    assert agreement["agrees"] is False
    assert agreement["escalated"] is False


def test_missing_barrier_on_high_energy_report_is_needs_more_info_regardless_of_model():
    bucket, _confidence, _agreement = route_prediction(
        sif_potential=True,
        base_confidence=0.8,
        decision_factors={"is_high_energy": True, "has_exposure": True, "energy_source": "model"},
        consistency_result=CONSISTENT,
        barrier_status="not_mentioned",
        model_signal={"sif_potential": True, "confidence": 0.99, "model_version": "test-model"},
    )
    assert bucket == NEEDS_MORE_INFO


class TestEnergyClassifierModelSignal:
    """energy_classifier.classify_energy must expose the active model's raw
    sif_potential/confidence as `sif_signal` (or None when no model ran) so
    Stage 3 has something to cross-check against — see pipeline.run_single."""

    def test_baseline2_produces_a_usable_sif_signal(self):
        from sif_engine.extraction.energy_classifier import classify_energy

        result = classify_energy(
            raw_text=(
                "Crew was working under a suspended load with no exclusion zone "
                "or tagline, isolation not verified before hot work began."
            ),
            model_name="baseline2",  # always committed to git, unlike the transformer checkpoint
        )
        signal = result.get("sif_signal")
        assert signal is not None
        assert isinstance(signal["sif_potential"], bool)
        assert 0.0 <= signal["confidence"] <= 1.0
        assert signal["model_version"]

    def test_unknown_model_name_degrades_to_no_signal_not_a_crash(self):
        from sif_engine.extraction.energy_classifier import classify_energy

        result = classify_energy(raw_text="Routine inspection, nothing noted.", model_name="not-a-real-model")
        assert result.get("sif_signal") is None
