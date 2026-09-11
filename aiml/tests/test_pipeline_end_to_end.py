"""
End-to-end pipeline tests for sif_engine.
"""

import pytest
from sif_engine.pipeline import run_single, run_batch, get_model_status


def test_run_single_output_contract():
    """Verify run_single produces the complete required schema."""
    report_text = (
        "During maintenance on process equipment at Rig 4, a worker was standing "
        "within the immediate hazard zone. Isolation status was not clearly "
        "confirmed by the crew. No injury occurred."
    )
    result = run_single(report_id="rep_test_01", report_text=report_text, site="Rig 4")

    assert result["report_id"] == "rep_test_01"
    assert result["site"] == "Rig 4"
    assert "extracted_fields" in result
    extracted = result["extracted_fields"]
    assert "activity" in extracted
    assert "energy_type" in extracted
    assert "barrier_status" in extracted
    assert "exposure" in extracted

    assert "classification" in result
    clf = result["classification"]
    assert isinstance(clf["sif_potential"], bool)
    assert 0.0 <= clf["confidence"] <= 1.0
    assert clf["bucket"] in ["HIGH_CONF_SIF", "LOW_CONF_REVIEW", "HIGH_CONF_NON_SIF", "NEEDS_MORE_INFO"]
    assert isinstance(clf["lsr_tag"], str)
    assert isinstance(clf["model_version"], str) and clf["model_version"]


def test_run_batch_processing():
    """Verify run_batch processes multiple reports correctly."""
    reports = [
        {"report_id": "b1", "report_text": "Welding without hot work permit near tank.", "site": "Rig 7"},
        {"report_id": "b2", "report_text": "Floor cleaned in warehouse, no hazards found.", "site": "Terminal A"},
    ]
    results = run_batch(reports)
    assert len(results) == 2
    assert results[0]["report_id"] == "b1"
    assert results[1]["report_id"] == "b2"
    assert isinstance(results[0]["classification"]["model_version"], str)


def test_model_status():
    """Verify get_model_status provides runtime metadata.

    active_sif_model legitimately varies with whether the gitignored
    transformer checkpoint happens to be present on this checkout (see
    ModelRegistry.get_configured_model_name) - assert the invariant, not a
    literal that would make this test fail on whichever machine trained it.
    """
    status = get_model_status()
    assert status["active_sif_model"] in ("baseline2", "transformer")
    assert status["mlp_available"] is True
    if status.get("transformer_available"):
        assert status["active_sif_model"] == "transformer"


if __name__ == "__main__":
    pytest.main([__file__])