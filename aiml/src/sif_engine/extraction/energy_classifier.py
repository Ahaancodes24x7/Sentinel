"""Energy Type Classifier for SIF Precursor Detection.

Classifies report text into canonical energy types defined in configs/ontology.yaml.
Supports:
1. Trained model inference (source: "model")
2. Deterministic keyword/ontology fallback (source: "fallback") with explicit
   confidence penalty and transparent provenance tracking.
"""

from pathlib import Path
from typing import Any, Optional
import yaml

# ---------------------------------------------------------------------------
# Canonical Ontology Mapping
# ---------------------------------------------------------------------------
ENERGY_TYPE_METADATA = {
    "stored/electrical energy": {"is_high_energy": True, "lsr_tag": "Energy Isolation"},
    "thermal (hot work)": {"is_high_energy": True, "lsr_tag": "Hot Work"},
    "gravitational (suspended load)": {"is_high_energy": True, "lsr_tag": "Safe Mechanical Lifting"},
    "kinetic (line of fire)": {"is_high_energy": True, "lsr_tag": "Line of Fire"},
    "atmospheric/asphyxiation": {"is_high_energy": True, "lsr_tag": "Confined Space"},
    "vehicular/motion": {"is_high_energy": True, "lsr_tag": "Driving"},
    "fall from height": {"is_high_energy": True, "lsr_tag": "Working at Height"},
    "low-energy/ergonomic": {"is_high_energy": False, "lsr_tag": "Work Authorisation"},
}

HAZARD_TO_ENERGY_MAP = {
    "energy_isolation": "stored/electrical energy",
    "hot_work": "thermal (hot work)",
    "confined_space": "atmospheric/asphyxiation",
    "line_of_fire": "kinetic (line of fire)",
    "safe_mechanical_lifting": "gravitational (suspended load)",
    "working_at_height": "fall from height",
    "driving": "vehicular/motion",
    "excavation": "stored/electrical energy",
}

_TRAINED_MODEL = None
_MODEL_TRIED = False


def _try_load_model():
    """Attempt to load a trained model if available on disk."""
    global _TRAINED_MODEL, _MODEL_TRIED
    if _MODEL_TRIED:
        return _TRAINED_MODEL
    _MODEL_TRIED = True

    model_dir = Path(__file__).resolve().parent.parent.parent.parent / "models"
    model_path = model_dir / "energy_classifier.joblib"
    if model_path.is_file():
        try:
            import joblib
            _TRAINED_MODEL = joblib.load(model_path)
        except Exception:
            _TRAINED_MODEL = None
    return _TRAINED_MODEL


LSR_TO_ENERGY_MAP = {
    "Energy Isolation": "stored/electrical energy",
    "Hot Work": "thermal (hot work)",
    "Safe Mechanical Lifting": "gravitational (suspended load)",
    "Line of Fire": "kinetic (line of fire)",
    "Confined Space": "atmospheric/asphyxiation",
    "Driving": "vehicular/motion",
    "Working at Height": "fall from height",
    "Work Authorisation": "low-energy/ergonomic",
    "Bypassing Safety Controls": "stored/electrical energy",
}


def classify_energy(
    raw_text: str,
    preprocessed_text: Optional[str] = None,
    hazard_category: Optional[str] = None,
    model_name: Optional[str] = None,
) -> dict[str, Any]:
    """Classify the report's energy type with explicit source provenance.
    
    Returns:
        dict with:
            - label: canonical energy type
            - confidence: float in [0.0, 1.0]
            - is_high_energy: bool
            - source: "model" | "fallback"
            - lsr_tag: mapped LSR category
            - model_version: model version string
    """
    target_text = preprocessed_text or raw_text

    # 1. Active trained model pathway (ModelRegistry: baseline2 / mlp)
    try:
        from sif_engine.inference.model_registry import get_model, get_active_model
        model = get_model(model_name) if model_name else get_active_model()
        if model is not None:
            pred = model.predict(target_text)
            predicted_lsr = pred.get("lsr_tag", "Work Authorisation")
            mapped_energy = LSR_TO_ENERGY_MAP.get(predicted_lsr, "stored/electrical energy")
            meta = ENERGY_TYPE_METADATA.get(
                mapped_energy, {"is_high_energy": True, "lsr_tag": predicted_lsr}
            )
            return {
                "label": mapped_energy,
                "confidence": round(float(pred.get("confidence", 0.85)), 3),
                "is_high_energy": meta["is_high_energy"],
                "source": "model",
                "lsr_tag": predicted_lsr,
                "model_version": pred.get("model_version", "baseline2-v0.3"),
            }
    except Exception:
        pass  # Fall through to fallback

    # 2. Transparent Fallback pathway (reduced confidence, marked source="fallback")
    if hazard_category and hazard_category in HAZARD_TO_ENERGY_MAP:
        mapped_energy = HAZARD_TO_ENERGY_MAP[hazard_category]
        meta = ENERGY_TYPE_METADATA.get(
            mapped_energy, {"is_high_energy": True, "lsr_tag": "Other"}
        )
        # Reduced confidence due to heuristic fallback
        return {
            "label": mapped_energy,
            "confidence": 0.65,
            "is_high_energy": meta["is_high_energy"],
            "source": "fallback",
            "lsr_tag": meta["lsr_tag"],
        }

    # Default low-energy fallback when no hazard cues match
    meta = ENERGY_TYPE_METADATA["low-energy/ergonomic"]
    return {
        "label": "low-energy/ergonomic",
        "confidence": 0.45,
        "is_high_energy": False,
        "source": "fallback",
        "lsr_tag": meta["lsr_tag"],
    }


def classify_energy_type(text: str) -> tuple[str, float]:
    """Legacy backward-compatible API: returns (label, confidence)."""
    res = classify_energy(raw_text=text)
    return res["label"], res["confidence"]