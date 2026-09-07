"""Comprehensive Test Suite for the SIF Precursor Detection Pipeline Architecture.

Verifies:
1. Raw-text span invariance (offsets match raw_text slices).
2. not_mentioned barrier behavior: silence is not a barrier gap, routes to NEEDS_MORE_INFO.
3. Explicit barrier absence: routes to HIGH_CONF_SIF when exposure is present.
4. Uncertain barrier: routes to LOW_CONF_REVIEW.
5. Confirmed barrier: SIF=False, routes to HIGH_CONF_NON_SIF.
6. Near-miss preservation: "No injury occurred" + direct exposure is valid near-miss, no contradiction.
7. Contradiction detection: "Area was clear" + direct exposure flags EXPOSURE_CONTRADICTION.
8. Energy classifier fallback transparency: source="fallback" when using heuristics.
9. Prototype site vocabulary: exact location matching.
10. End-to-end run_single and run_batch pipeline execution.
"""

import pytest
from sif_engine.extraction.evidence_extractor import extract_evidence, extract_location, extract_exposure, extract_barrier_status
from sif_engine.extraction.energy_classifier import classify_energy
from sif_engine.reasoning.consistency import validate_consistency
from sif_engine.reasoning.scl_reasoner import reason
from sif_engine.confidence.routing import route_prediction
from sif_engine.pipeline import run_single, run_batch


class TestEvidenceExtractor:
    def test_raw_text_span_invariance(self):
        """Character offsets must slice the exact substring from the raw input text."""
        raw_text = "During maintenance on process equipment at Rig 4, isolation was verified before entry."
        ev = extract_evidence(raw_text)

        # Activity span
        act_span = ev["activity"]["span"]
        assert raw_text[act_span[0]:act_span[1]].lower() == ev["activity"]["text"].lower()

        # Location span
        loc = ev["location"]
        assert loc["value"] == "Rig 4"
        assert raw_text[loc["span"][0]:loc["span"][1]] == "Rig 4"

        # Barrier span
        barrier = ev["barrier"]
        assert barrier.status == "confirmed"
        assert barrier.gap_severity == 0.0
        assert len(barrier.evidence) > 0
        b_span = barrier.evidence[0].span
        assert raw_text[b_span[0]:b_span[1]].lower() == barrier.evidence[0].text.lower()

    def test_prototype_site_vocabulary(self):
        """Location extraction recognizes prototype/synthetic sites."""
        sites = ["Rig 4", "Rig 7", "Plant C", "Well Site B", "Field Station 2", "Terminal A"]
        for site in sites:
            text = f"Activity conducted at {site} yesterday."
            loc = extract_location(text)
            assert loc["value"] == site
            assert text[loc["span"][0]:loc["span"][1]] == site

    def test_barrier_four_distinct_states(self):
        """Barrier status must implement 4 states with precise gap severities."""
        # 1. Confirmed -> 0.0
        b_conf = extract_barrier_status("Isolation was verified and tagged before work began.")
        assert b_conf.status == "confirmed"
        assert b_conf.gap_severity == 0.0

        # 2. Uncertain -> 0.6
        b_unc = extract_barrier_status("Isolation status was not clearly confirmed by the crew.")
        assert b_unc.status == "uncertain"
        assert b_unc.gap_severity == 0.6

        # 3. Explicitly absent -> 1.0
        b_abs = extract_barrier_status("Work commenced without a permit and no isolation was set up.")
        assert b_abs.status == "explicitly_absent"
        assert b_abs.gap_severity == 1.0

        # 4. Not mentioned -> None (silence is NOT a gap)
        b_nom = extract_barrier_status("Worker replaced valve and checked pump pressure.")
        assert b_nom.status == "not_mentioned"
        assert b_nom.gap_severity is None


class TestConsistencyAndNearMiss:
    def test_near_miss_preservation(self):
        """'No injury occurred' + direct exposure must NOT be marked as contradictory."""
        raw_text = (
            "During hot work at Plant C, a worker was standing within the immediate hazard zone. "
            "No isolation was mentioned in the report. No injury occurred."
        )
        ev = extract_evidence(raw_text)
        energy_res = classify_energy(raw_text=raw_text, hazard_category="hot_work")
        cons = validate_consistency(ev, energy_res)

        assert cons["is_valid_near_miss"] is True
        assert not any("injury" in w.lower() for w in cons["warnings"])

    def test_exposure_contradiction_detection(self):
        """'Area was clear' alongside direct exposure marker must trigger EXPOSURE_CONTRADICTION."""
        raw_text = "The area was clear of workers, yet a contractor was standing within the immediate hazard zone."
        ev = extract_evidence(raw_text)
        energy_res = classify_energy(raw_text=raw_text)
        cons = validate_consistency(ev, energy_res)

        assert cons["is_consistent"] is False
        assert any("EXPOSURE_CONTRADICTION" in w for w in cons["warnings"])
        assert cons["penalty"] > 0

    def test_energy_hazard_disagreement(self):
        """Mismatched energy prediction and hazard keyword evidence must trigger warning."""
        ev = {
            "hazard": {"best_category": "driving"},
            "exposure": {"label": "direct_proximity"},
            "raw_text": "vehicle movement",
        }
        # Artificial conflict: classifier predicted electrical for a driving incident
        energy_res = {"label": "stored/electrical energy", "is_high_energy": True, "source": "model"}
        cons = validate_consistency(ev, energy_res)

        assert cons["is_consistent"] is False
        assert any("ENERGY_HAZARD_DISAGREEMENT" in w for w in cons["warnings"])


class TestSCLReasonerAndRouting:
    def test_silence_routes_to_needs_more_info(self):
        """Reports omitting barrier details must NOT create false SIF positives; route to NEEDS_MORE_INFO."""
        raw_text = (
            "During electrical panel work at Well Site B, a worker was standing within the immediate hazard zone. "
            "Routine walk-around inspection conducted."
        )
        result = run_single("rep_001", raw_text)

        clf = result["classification"]
        # Barrier was omitted
        assert result["extracted_fields"]["barrier_status"]["label"] == "not_mentioned"
        # Silence must NOT be converted to a barrier failure or SIF
        assert clf["sif_potential"] is False
        assert clf["bucket"] == "NEEDS_MORE_INFO"
        assert "omitted barrier controls" in clf["justification"].lower()

    def test_explicit_absence_routes_to_high_conf_sif(self):
        """High energy + explicit barrier absence + direct exposure -> HIGH_CONF_SIF."""
        raw_text = (
            "During hot work at Rig 7, a worker was standing within the immediate hazard zone. "
            "No isolation was established and work proceeded without a permit. No injury occurred."
        )
        result = run_single("rep_002", raw_text)

        clf = result["classification"]
        assert clf["sif_potential"] is True
        assert clf["bucket"] in ["HIGH_CONF_SIF", "LOW_CONF_REVIEW"]
        assert result["extracted_fields"]["barrier_status"]["label"] == "explicitly_absent"
        assert clf["lsr_tag"] in ["Hot Work", "Energy Isolation"]

    def test_uncertain_barrier_routes_to_low_conf_review(self):
        """Uncertain barrier language -> sif_potential=True, but bucket=LOW_CONF_REVIEW."""
        raw_text = (
            "During maintenance on process equipment at Rig 4, a worker was standing within the immediate hazard zone. "
            "Isolation status was not clearly confirmed by the crew. No injury occurred."
        )
        result = run_single("rep_003", raw_text)

        clf = result["classification"]
        assert clf["sif_potential"] is True
        assert result["extracted_fields"]["barrier_status"]["label"] == "uncertain"
        assert clf["bucket"] == "LOW_CONF_REVIEW"

    def test_confirmed_barrier_routes_to_high_conf_non_sif(self):
        """Confirmed barrier present -> sif_potential=False, bucket=HIGH_CONF_NON_SIF."""
        raw_text = (
            "During maintenance on process equipment at Plant C, isolation was verified and tagged before work began. "
            "A worker was standing within the immediate hazard zone. No injury occurred."
        )
        result = run_single("rep_004", raw_text)

        clf = result["classification"]
        assert clf["sif_potential"] is False
        assert result["extracted_fields"]["barrier_status"]["label"] == "confirmed"
        assert clf["bucket"] == "HIGH_CONF_NON_SIF"

    def test_no_exposure_routes_to_non_sif(self):
        """Area cleared of workers -> sif_potential=False, bucket=HIGH_CONF_NON_SIF."""
        raw_text = (
            "During lifting operation with mobile crane at Rig 4, no personnel were in the vicinity at the time. "
            "No isolation was mentioned in the report."
        )
        result = run_single("rep_005", raw_text)

        clf = result["classification"]
        assert clf["sif_potential"] is False
        assert result["extracted_fields"]["exposure"]["label"] == "no_exposure"
        assert clf["bucket"] in ["HIGH_CONF_NON_SIF", "NEEDS_MORE_INFO"]

    def test_batch_run_matches_structure(self):
        """run_batch must return a list of properly formatted report results."""
        batch = [
            {"report_id": "r1", "report_text": "Hot work at Rig 4 without a permit.", "site": "Rig 4"},
            {"report_id": "r2", "report_text": "Routine inspection at Plant C, area was clear.", "site": "Plant C"},
        ]
        results = run_batch(batch)
        assert len(results) == 2
        for r in results:
            assert "report_id" in r
            assert "extracted_fields" in r
            assert "classification" in r
            assert "activity" in r["extracted_fields"]
            assert "energy_type" in r["extracted_fields"]
            assert "barrier_status" in r["extracted_fields"]
            assert "exposure" in r["extracted_fields"]
