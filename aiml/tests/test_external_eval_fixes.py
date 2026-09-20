"""Regression tests for the Week 1 external-evaluation fixes (Phase 8).

Each test traces to a specific finding in
`reports/week1_external_error_analysis.md` and a specific external narrative
in `data/external_eval/narratives.jsonl`. These lock in the two fixes made
after the Week 1 report shipped:

1. The high-energy rule gate's `working_at_height` hazard category matched
   the bare word "fall" (ext_005: "the water level to fall" - an
   environmental release with zero personnel-height pathway - falsely set
   `is_high_energy=True`).
2. `EXPLICIT_ABSENCE_PHRASES` had no real-world barrier-absence construction
   ("...procedures were not in use", ext_020), so extraction returned
   `not_mentioned` instead of `explicitly_absent` even when the source text
   explicitly stated a barrier was absent.
"""

from sif_engine.extraction.energy_classifier import evaluate_high_energy_gate
from sif_engine.extraction.evidence_extractor import extract_barrier_status


class TestHighEnergyFalseTriggerFix:
    """ext_005 (Njord A oil spill) — bare "fall" false-triggered
    working_at_height on a level-control/environmental narrative."""

    def test_level_falling_does_not_trigger_working_at_height(self):
        text = (
            "The water level began to fall as the valve remained in a fixed "
            "position, allowing oil to discharge to sea."
        )
        gate = evaluate_high_energy_gate(text, hazard_category="working_at_height")
        # hazard_category is passed in deliberately (as the pipeline would),
        # so this asserts the CUE-BASED path specifically does not also fire
        # on "fall" — the hazard_category fallback is a separate, legitimate
        # path this test does not exercise.
        assert "fall" not in gate["high_energy_evidence"]

    def test_person_falling_from_height_still_triggers(self):
        """The fix must not blunt recall on the thing this hazard category
        exists to catch — verified against ext_004's actual construction."""
        text = "A scaffolding worker fell 4.4 metres from formwork scaffolding onto concrete flooring."
        gate = evaluate_high_energy_gate(text)
        assert gate["high_energy_decision"] is True

    def test_explicit_fall_from_height_phrase_still_matches(self):
        text = "The worker suffered a fall from height while accessing the platform."
        gate = evaluate_high_energy_gate(text)
        assert gate["high_energy_decision"] is True


class TestBarrierAbsencePhraseExpansion:
    """ext_020 (IADC PRS/LOTO near-miss) and related — real-world absence
    constructions the synthetic-tuned phrase list had no entry for."""

    def test_procedures_were_not_in_use_is_explicitly_absent(self):
        # Verbatim from ext_020's source text.
        text = "The investigation found that lock-out/tag-out procedures were not in use."
        result = extract_barrier_status(text)
        assert result.status == "explicitly_absent"
        assert result.gap_severity == 1.0

    def test_harness_was_not_attached_is_explicitly_absent(self):
        # Verbatim from ext_004's source text.
        text = "His fall-arrest harness with dual lanyard and shock absorber was not attached to a secure anchor point."
        result = extract_barrier_status(text)
        assert result.status == "explicitly_absent"

    def test_failure_to_follow_procedures_is_explicitly_absent(self):
        # Verbatim from ext_009's source text.
        text = "The investigation cited failure to follow red-zone procedures during the lift."
        result = extract_barrier_status(text)
        assert result.status == "explicitly_absent"

    def test_barrier_had_failed_is_explicitly_absent(self):
        # Paraphrased from ext_012's source text ("the outer well barrier had failed").
        text = "The outer well barrier had failed, releasing gas that had accumulated behind the casing."
        result = extract_barrier_status(text)
        assert result.status == "explicitly_absent"

    def test_confirmed_barrier_language_is_unaffected(self):
        """The expansion must not make confirmed barriers look absent —
        regression guard against overly broad phrase additions."""
        text = "Isolation was confirmed and the permit was signed before work began."
        result = extract_barrier_status(text)
        assert result.status == "confirmed"
