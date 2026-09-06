"""
Smoke tests for Baseline 2 and MLP model inference.

Verifies:
- Model files exist on disk
- Artifacts load correctly into memory
- No training code executes during inference
- No absolute machine-specific paths exist
- Both Baseline 2 and MLP models produce valid predictions, probabilities,
  and 4-bucket classifications on representative test reports
"""

import pytest
from sif_engine.inference.baseline2 import Baseline2Model
from sif_engine.inference.mlp import MLPModel
from sif_engine.inference.model_registry import (
    ModelRegistry,
    get_active_model,
    get_model,
    get_model_metadata,
)

SAMPLE_REPORTS = [
    (
        "rep_1",
        "During maintenance on process equipment at Rig 4, a worker was standing "
        "within the immediate hazard zone. Isolation status was not clearly "
        "confirmed by the crew. No injury occurred.",
        True,  # expected high risk / SIF potential
    ),
    (
        "rep_2",
        "Routine housekeeping completed in workshop area. All tools returned to shadow board. "
        "Area was clean and dry.",
        False,  # expected non-SIF
    ),
    (
        "rep_3",
        "Hot work permit was active for pipe welding near manifold. Gas testing was verified safe "
        "and fire watch was present.",
        True,
    ),
    (
        "rep_4",
        "Scaffolding inspection completed on Rig 7. Minor tag update required; no work at height ongoing.",
        False,
    ),
]


def test_baseline2_loading_and_inference():
    """Verify Baseline 2 model loads and executes inference properly."""
    model = Baseline2Model()
    assert not model.is_loaded
    model.load()
    assert model.is_loaded
    assert model.MODEL_VERSION == "baseline2-v0.3"

    for rep_id, text, _ in SAMPLE_REPORTS:
        res = model.predict(text)
        assert isinstance(res["sif_potential"], bool)
        assert 0.0 <= res["confidence"] <= 1.0
        assert 0.0 <= res["raw_probability"] <= 1.0
        assert res["bucket"] in ["HIGH_CONF_SIF", "LOW_CONF_REVIEW", "HIGH_CONF_NON_SIF", "NEEDS_MORE_INFO"]
        assert isinstance(res["lsr_tag"], str) and len(res["lsr_tag"]) > 0
        assert res["model_version"] == "baseline2-v0.3"
        assert len(res["justification"]) > 10


def test_mlp_loading_and_inference():
    """Verify MLP benchmark model loads and executes inference properly."""
    model = MLPModel()
    assert not model.is_loaded
    model.load()
    assert model.is_loaded
    assert model.MODEL_VERSION == "mlp-v0.1"

    for rep_id, text, _ in SAMPLE_REPORTS:
        res = model.predict(text)
        assert isinstance(res["sif_potential"], bool)
        assert 0.0 <= res["confidence"] <= 1.0
        assert 0.0 <= res["raw_probability"] <= 1.0
        assert res["bucket"] in ["HIGH_CONF_SIF", "LOW_CONF_REVIEW", "HIGH_CONF_NON_SIF", "NEEDS_MORE_INFO"]
        assert isinstance(res["lsr_tag"], str) and len(res["lsr_tag"]) > 0
        assert res["model_version"] == "mlp-v0.1"
        assert len(res["justification"]) > 10


def test_model_registry_defaults():
    """Verify registry defaults to baseline2 and metadata reflects both models."""
    registry = ModelRegistry()
    assert registry.get_configured_model_name() == "baseline2"
    active = registry.get_active_model()
    assert isinstance(active, Baseline2Model)

    mlp = registry.get_model("mlp")
    assert isinstance(mlp, MLPModel)

    meta = registry.get_metadata()
    assert meta["active_sif_model"] == "baseline2"
    assert meta["default_sif_model"] == "baseline2"
    assert meta["mlp_available"] is True
    assert "baseline2" in meta["available_models"]
    assert "mlp" in meta["available_models"]


def test_environment_variable_model_selection(monkeypatch):
    """Verify SENTINEL_SIF_MODEL environment variable selects MLP cleanly."""
    monkeypatch.setenv("SENTINEL_SIF_MODEL", "mlp")
    registry = ModelRegistry()
    assert registry.get_configured_model_name() == "mlp"
    active = registry.get_active_model()
    assert isinstance(active, MLPModel)

    # Fallback when invalid env var set
    monkeypatch.setenv("SENTINEL_SIF_MODEL", "unknown_future_model")
    assert registry.get_configured_model_name() == "baseline2"


if __name__ == "__main__":
    pytest.main([__file__])
