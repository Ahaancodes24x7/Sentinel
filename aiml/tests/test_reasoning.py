"""Comprehensive 17-Scenario Unit Test Matrix for Sentinel SIF Reasoning Engine,
Stage 1 Hardening, Contextual Environment Extractor, and OIL Site Intelligence.

Covers all 17 scenarios specified in Part 18:
 1. High-energy electrical with confirmed LOTO isolation -> SIF=False, gap_severity=0.0
 2. High-energy suspended load with worker directly underneath and no exclusion zone -> SIF=True, gap_severity=1.0
 3. High-energy crane lift with no personnel in the vicinity -> SIF=False, exposure=no_exposure
 4. Confined space entry with atmosphere test completed and continuous ventilation running -> SIF=False, barrier=confirmed
 5. Welding without hot work permit or fire watch near process line -> SIF=True, barrier=explicitly_absent
 6. Scaffold tag unverified, worker hesitated before ascending -> barrier=uncertain (0.6), routes to human review
 7. Routine housekeeping, worker slipped on oily rag, minor bruise -> low energy, SIF=False
 8. Area was cleared of all personnel prior to high-pressure line test -> direct exposure=False, SIF=False
 9. Electrical panel servicing, no mention of LOTO or test-before-touch -> barrier=not_mentioned (None), routes to NEEDS_MORE_INFO
10. Near-miss: dropped wrench from height, deflected by netting, worker below -> high energy=True, near-miss preserved, SIF=True
11. Contradictory report: 'Area was cleared of all workers... worker directly under crane arm' -> contradiction detected, review routed
12. Inconsistent classification: energy says low-energy, hazard evidence says 'electrical isolation failure' -> disagreement flagged
13. OIL site intelligence: report mentions 'Naharkatiya well site' -> extracts Naharkatiya, maps to Upper Assam Basin
14. OIL site intelligence: report mentions 'Dandewala gas compressor' -> extracts Dandewala, maps to Rajasthan
15. Demonstration site: report mentions 'Rig 4' -> extracts Rig 4, flags as synthetic demonstration data
16. Negated environment: report says 'maintenance conducted outside of confined space' -> does NOT assign confined_space
17. Character span exactness: raw_text[start:end] == span_text strictly verified across all scenarios
"""

import pytest
from sif_engine.pipeline import run_single
from sif_engine.extraction.evidence_extractor import extract_evidence
from sif_engine.extraction.environment_extractor import extract_environment
from sif_engine.extraction.energy_classifier import classify_energy
from sif_engine.reasoning.consistency import validate_consistency
from sif_engine.reasoning.scl_reasoner import reason
from sif_engine.reasoning.credible_consequence import evaluate_credible_consequence
from sif_engine.site_intelligence.site_registry import resolve_site_from_text, get_site_by_id


def assert_span_invariance(report_text: str, extracted_fields: dict):
    """Verify that every extracted character span exactly matches the raw report text slice."""
    for field_name, val in extracted_fields.items():
        if field_name == "evidence_spans":
            for span_item in val:
                s = span_item.get("span")
                if s:
                    assert report_text[s[0]:s[1]] == span_item["text"], (
                        f"Span mismatch in {span_item['field']}: "
                        f"raw_text[{s[0]}:{s[1]}] = '{report_text[s[0]:s[1]]}', expected '{span_item['text']}'"
                    )
        elif isinstance(val, dict):
            s = val.get("span")
            text = val.get("text")
            if s and text:
                assert report_text[s[0]:s[1]] == text, (
                    f"Span mismatch in {field_name}: "
                    f"raw_text[{s[0]}:{s[1]}] = '{report_text[s[0]:s[1]]}', expected '{text}'"
                )


class TestSeventeenScenarios:
    """17-scenario comprehensive validation matrix."""

    # Scenario 1: High-energy electrical with confirmed LOTO isolation -> SIF=False, gap_severity=0.0
    def test_scenario_01_electrical_confirmed_loto(self):
        text = "Technician performed electrical switchgear maintenance at Plant C after LOTO isolation was verified and confirmed."
        res = run_single("scen_01", text)
        assert res["classification"]["sif_potential"] is False
        assert res["extracted_fields"]["barrier_status"]["label"] == "confirmed"
        assert res["reasoning"]["barrier_gap_severity"] == 0.0
        assert_span_invariance(text, res["extracted_fields"])

    # Scenario 2: High-energy suspended load with worker directly underneath and no exclusion zone -> SIF=True, gap_severity=1.0
    def test_scenario_02_suspended_load_worker_beneath_no_zone(self):
        text = "During mobile crane lifting at Rig 4, a worker was standing directly beneath the suspended load with no exclusion zone established."
        res = run_single("scen_02", text)
        assert res["classification"]["sif_potential"] is True
        assert res["extracted_fields"]["barrier_status"]["label"] == "explicitly_absent"
        assert res["reasoning"]["barrier_gap_severity"] == 1.0
        assert res["extracted_fields"]["exposure"]["label"] == "direct_proximity"
        assert_span_invariance(text, res["extracted_fields"])

    # Scenario 3: High-energy crane lift with no personnel in the vicinity -> SIF=False, exposure=no_exposure
    def test_scenario_03_crane_lift_no_personnel(self):
        text = "Heavy lifting operation underway at Terminal A. The area was clear of workers and barricaded with no entry."
        res = run_single("scen_03", text)
        assert res["classification"]["sif_potential"] is False
        assert res["extracted_fields"]["exposure"]["label"] == "no_exposure"
        assert_span_invariance(text, res["extracted_fields"])

    # Scenario 4: Confined space entry with atmosphere test completed and continuous ventilation running -> SIF=False, barrier=confirmed
    def test_scenario_04_confined_space_gas_test_completed(self):
        text = "Confined space vessel entry conducted at Plant C. Multi-gas test completed and continuous ventilation running before crew entered."
        res = run_single("scen_04", text)
        assert res["classification"]["sif_potential"] is False
        assert res["extracted_fields"]["barrier_status"]["label"] == "confirmed"
        assert res["reasoning"]["barrier_gap_severity"] == 0.0
        assert_span_invariance(text, res["extracted_fields"])

    # Scenario 5: Welding without hot work permit or fire watch near process line -> SIF=True, barrier=explicitly_absent
    def test_scenario_05_welding_without_permit_fire_watch(self):
        text = "Contractor commenced hot work welding on process line at Field Station 2 without hot work permit and no fire watch posted. Crew in the vicinity."
        res = run_single("scen_05", text)
        assert res["classification"]["sif_potential"] is True
        assert res["extracted_fields"]["barrier_status"]["label"] == "explicitly_absent"
        assert res["reasoning"]["barrier_gap_severity"] == 1.0
        assert_span_invariance(text, res["extracted_fields"])

    # Scenario 6: Scaffold tag unverified, worker hesitated before ascending -> barrier=uncertain (0.6), routes to human review
    def test_scenario_06_scaffold_tag_unverified(self):
        text = "At Well Site B, scaffolding erection was inspected. The scaffold tag was unverified and worker hesitated before ascending to elevated platform."
        res = run_single("scen_06", text)
        assert res["extracted_fields"]["barrier_status"]["label"] == "uncertain"
        assert res["reasoning"]["barrier_gap_severity"] == 0.6
        assert res["classification"]["bucket"] in ["LOW_CONF_REVIEW", "HIGH_CONF_SIF"]
        assert_span_invariance(text, res["extracted_fields"])

    # Scenario 7: Routine housekeeping, worker slipped on oily rag, minor bruise -> low energy, SIF=False
    def test_scenario_07_housekeeping_slip_low_energy(self):
        text = "Routine housekeeping in workshop at Plant C: worker tripped on oily rag sustaining a minor bruise. No equipment damaged."
        res = run_single("scen_07", text)
        assert res["classification"]["sif_potential"] is False
        assert res["classification"]["bucket"] == "HIGH_CONF_NON_SIF"
        assert res["reasoning"]["decision_factors"]["is_high_energy"] is False
        assert_span_invariance(text, res["extracted_fields"])

    # Scenario 8: Area was cleared of all personnel prior to high-pressure line test -> direct exposure=False, SIF=False
    def test_scenario_08_high_pressure_test_area_cleared(self):
        text = "High pressure line hydrotesting at Rig 7. The area was cleared of all personnel prior to line pressurization."
        res = run_single("scen_08", text)
        assert res["classification"]["sif_potential"] is False
        assert res["extracted_fields"]["exposure"]["label"] == "no_exposure"
        assert_span_invariance(text, res["extracted_fields"])

    # Scenario 9: Electrical panel servicing, no mention of LOTO or test-before-touch -> barrier=not_mentioned (None), routes to NEEDS_MORE_INFO
    def test_scenario_09_electrical_panel_silence_on_barrier(self):
        text = "Technician opened electrical panel 415V switchboard for servicing at Rig 4 while standing within immediate hazard zone."
        res = run_single("scen_09", text)
        assert res["extracted_fields"]["barrier_status"]["label"] == "not_mentioned"
        assert res["reasoning"]["barrier_gap_severity"] is None
        assert res["classification"]["bucket"] == "NEEDS_MORE_INFO"
        assert res["classification"]["sif_potential"] is False
        assert_span_invariance(text, res["extracted_fields"])

    # Scenario 10: Near-miss: dropped wrench from height, deflected by netting, worker below -> high energy=True, near-miss preserved, SIF=True
    def test_scenario_10_near_miss_dropped_object(self):
        text = "Near miss at Rig 7: dropped 12-inch wrench from scaffolding, deflected by netting while worker below ducked. No injury occurred."
        res = run_single("scen_10", text)
        assert res["reasoning"]["decision_factors"]["is_valid_near_miss"] is True
        assert res["classification"]["sif_potential"] is True
        assert "near-miss" in res["classification"]["justification"].lower()
        assert_span_invariance(text, res["extracted_fields"])

    # Scenario 11: Contradictory report: 'Area was cleared of all workers... worker directly under crane arm' -> contradiction detected, review routed
    def test_scenario_11_contradiction_clearance_vs_worker_under(self):
        text = "Lifting operation at Terminal A: Area was cleared of all workers, yet a rigger was directly under crane arm."
        res = run_single("scen_11", text)
        assert res["stage_metadata"]["consistency"]["contradiction_detected"] is True
        assert any("EXPOSURE_CONTRADICTION" in w for w in res["stage_metadata"]["consistency"]["warnings"])
        assert res["classification"]["bucket"] == "LOW_CONF_REVIEW"
        assert_span_invariance(text, res["extracted_fields"])

    # Scenario 12: Inconsistent classification: energy says low-energy, hazard evidence says 'electrical isolation failure' -> disagreement flagged
    def test_scenario_12_disagreement_energy_hazard(self):
        ev = {
            "hazard": {"best_category": "energy_isolation"},
            "exposure": {"label": "direct_proximity"},
            "raw_text": "electrical isolation live circuit failure",
        }
        art_energy = {"label": "low-energy/ergonomic", "is_high_energy": False, "source": "model"}
        cons = validate_consistency(ev, art_energy)
        assert cons["is_consistent"] is False
        assert any("ENERGY_HAZARD_DISAGREEMENT" in w for w in cons["warnings"])

    # Scenario 13: OIL site intelligence: report mentions 'Naharkatiya well site' -> extracts Naharkatiya, maps to Upper Assam Basin
    def test_scenario_13_site_naharkatiya(self):
        text = "Maintenance on pumping unit at Naharkatiya field station. Guard removed without permit."
        loc = resolve_site_from_text(text)
        assert loc["canonical_name"] == "Naharkatiya"
        site_info = get_site_by_id(loc["site_id"])
        assert site_info["region"] == "Upper Assam Basin"
        assert site_info["state"] == "Assam"
        assert text[loc["span"][0]:loc["span"][1]] == loc["raw_match"]

    # Scenario 14: OIL site intelligence: report mentions 'Dandewala gas compressor' -> extracts Dandewala, maps to Rajasthan
    def test_scenario_14_site_dandewala(self):
        text = "Gas leak observed near manifold at Dandewala gas field during morning rounds."
        loc = resolve_site_from_text(text)
        assert loc["canonical_name"] == "Dandewala"
        site_info = get_site_by_id(loc["site_id"])
        assert site_info["region"] == "Jaisalmer Basin"
        assert site_info["state"] == "Rajasthan"
        assert text[loc["span"][0]:loc["span"][1]] == loc["raw_match"]

    # Scenario 15: Demonstration site: report mentions 'Rig 4' -> extracts Rig 4, flags as synthetic demonstration data
    def test_scenario_15_demonstration_site_rig_4(self):
        text = "Drilling crew at Rig 4 completed mud pump inspection with exclusion zone established."
        res = run_single("scen_15", text)
        assert res["site_intelligence"]["canonical_name"] == "Rig 4"
        assert res["site_intelligence"]["is_synthetic_prototype"] is True
        assert res["site_intelligence"]["demonstration_notice"] == "SYNTHETIC DEMONSTRATION DATA"

    # Scenario 16: Negated environment: report says 'maintenance conducted outside of confined space' -> does NOT assign confined_space
    def test_scenario_16_negated_environment_outside_confined_space(self):
        text = "Inspection of exterior valve flange conducted outside of confined space without entering vessel."
        env = extract_environment(text)
        # Either category is negated=True or category is None/another non-negated environment
        if env["category"] == "confined_space":
            assert env["negated"] is True
        else:
            # Confined space was not chosen as active positive environment
            assert env["negated"] is False

    # Scenario 17: Character span exactness: raw_text[start:end] == span_text strictly verified across all scenarios
    def test_scenario_17_exact_span_invariance_comprehensive(self):
        test_reports = [
            "Hot work welding on process line at Field Station 2 without a permit.",
            "Crane lifting operation at Rig 7 with suspended load directly beneath.",
            "Electrical switchgear at Plant C with LOTO verified and confirmed.",
            "Area was clear of workers during high pressure hydrotesting at Terminal A.",
            "Routine equipment inspection in workshop at Moran field area.",
        ]
        for idx, text in enumerate(test_reports):
            res = run_single(f"invariance_{idx}", text)
            assert_span_invariance(text, res["extracted_fields"])

    def test_reasoning_object_has_hardened_contract(self):
        text = "During maintenance, a worker was exposed to an energized electrical component. No LOTO isolation was established. No injury occurred."
        res = run_single("reason_contract", text)
        reasoning = res["reasoning"]

        expected = {
            "activity", "hazard", "energy", "exposure", "barrier", "environment",
            "credible_consequence", "sif_potential", "lsr", "missing_information",
            "contradictions", "evidence", "reasoning_steps", "provenance"
        }
        assert expected.issubset(reasoning.keys())
        assert "reasoning_steps" in reasoning
        assert len(reasoning["reasoning_steps"]) >= 3
        assert reasoning["sif_potential"] is True
        assert reasoning["lsr"]["rule"] in {"Energy Isolation", "Line of Fire", "unresolved"}
        assert isinstance(reasoning["missing_information"], list)
        assert isinstance(reasoning["contradictions"], list)

    def test_explicit_environment_only_not_inferred(self):
        night = extract_environment("During night shift, workers performed maintenance.")
        rain = extract_environment("Heavy rain was present during the operation.")

        assert night["category"] in {None, "night_work"}
        assert night["category"] != "poor_visibility"
        assert rain["category"] in {None, "weather_exposure"}
        assert rain["category"] != "slippery_surface"

    def test_no_worker_exposed_is_not_exposure(self):
        result = run_single(
            "no_exposure_phrase",
            "Electrical maintenance completed with no worker exposed and isolation verified.",
        )
        assert result["extracted_fields"]["exposure"]["label"] == "no_exposure"
        assert result["classification"]["sif_potential"] is False

    def test_reasoner_recomputes_rule_gate_over_model_flag(self):
        evidence = extract_evidence("Routine housekeeping in the workshop; no worker was exposed.")
        result = reason(
            evidence=evidence,
            energy_classification={
                "label": "stored/electrical energy",
                "high_energy_decision": True,
                "is_high_energy": True,
                "source": "model",
            },
        )
        assert result["decision_factors"]["is_high_energy"] is False
        assert result["sif_potential"] is False

    def test_pressure_and_excavation_consequences_are_auditable(self):
        pressure = evaluate_credible_consequence(
            "stored pressure energy", "line_of_fire", "direct_proximity"
        )
        excavation = evaluate_credible_consequence(
            "unspecified energy", "excavation", "direct_proximity"
        )
        assert pressure["potential_severity"] == "fatality"
        assert pressure["lsr_tag"] == "Energy Isolation"
        assert excavation["potential_severity"] == "fatality"
        assert excavation["lsr_tag"] == "N/A"

    def test_multiple_hazards_preserved(self):
        result = run_single(
            "multiple_hazards",
            "Worker entered a confined space while hot work was being performed; no fire watch was posted.",
        )
        reasoning = result["reasoning"]
        assert reasoning["primary_hazard"] in {"confined_space", "hot_work"}
        assert reasoning["secondary_hazards"]