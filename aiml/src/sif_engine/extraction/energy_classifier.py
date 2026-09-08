"""Energy Type Classifier & High-Energy Gate for SIF Precursor Detection.

Classifies report text into canonical energy types defined in configs/ontology.yaml.
Supports:
1. Rule/evidence-based high-energy gate (empirical ablation: 0.779 recall, 0.781 F2)
2. Descriptive energy_type classification (model inference or ontology fallback)
3. Transparent provenance tracking (high_energy_source, high_energy_evidence, confidence)
"""

from pathlib import Path
from typing import Any, Optional
import re

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

# Explicit high-energy rule indicators (LSR high-energy hazard triggers)
HIGH_ENERGY_RULE_INDICATORS = {
    "stored/electrical energy": [
        "electrical", "energized", "live circuit", "live wire", "switchboard",
        "breaker", "isolation failure", "high voltage", "capacitor", "arc flash",
        "power line", "transformer"
    ],
    "thermal (hot work)": [
        "welding", "cutting torch", "grinding", "open flame", "torch", "hot work",
        "flammable vapor", "spark ignition"
    ],
    "gravitational (suspended load)": [
        "suspended load", "crane lift", "overhead lift", "rigging", "hoist line",
        "dropped object", "derrick lift", "winch cable"
    ],
    "kinetic (line of fire)": [
        "line of fire", "high pressure line", "kickback", "whip check",
        "pressurized hose", "rotating equipment", "pinch point", "flying debris"
    ],
    "atmospheric/asphyxiation": [
        "confined space", "h2s", "toxic gas", "oxygen deficient", "asphyxiation",
        "inert atmosphere", "tank entry", "vessel purge"
    ],
    "vehicular/motion": [
        "heavy vehicle", "forklift", "truck reversing", "mobile plant",
        "vehicle rollover", "transport collision"
    ],
    "fall from height": [
        "working at height", "elevated platform", "scaffolding", "ladder fall",
        "roof edge", "derrick mast", "fall arrest", "manlift"
    ],
}


def evaluate_high_energy_gate(raw_text: str, hazard_category: Optional[str] = None) -> dict[str, Any]:
    """Rule/evidence-based high-energy gate.
    
    Evaluates direct physical evidence of high-energy hazards in raw text.
    Outperforms multiclass TF-IDF classifier on SIF recall (0.779 vs 0.716) and F2 (0.781 vs 0.738).
    """
    raw_lower = raw_text.lower()
    matched_cues: list[str] = []
    matched_energy_types: list[str] = []

    for energy_type, cues in HIGH_ENERGY_RULE_INDICATORS.items():
        for cue in cues:
            if re.search(r"\b" + re.escape(cue) + r"\b", raw_lower):
                matched_cues.append(cue)
                if energy_type not in matched_energy_types:
                    matched_energy_types.append(energy_type)

    if matched_cues:
        primary_energy = matched_energy_types[0]
        return {
            "high_energy_decision": True,
            "high_energy_source": "rule_evidence_gate",
            "high_energy_confidence": min(0.70 + 0.05 * len(matched_cues), 0.95),
            "high_energy_evidence": matched_cues,
            "suggested_energy_type": primary_energy,
        }

    # Fallback to hazard category if present
    if hazard_category and hazard_category in HAZARD_TO_ENERGY_MAP:
        mapped_energy = HAZARD_TO_ENERGY_MAP[hazard_category]
        if mapped_energy != "low-energy/ergonomic":
            return {
                "high_energy_decision": True,
                "high_energy_source": "rule_evidence_gate",
                "high_energy_confidence": 0.80,
                "high_energy_evidence": [f"hazard_category:{hazard_category}"],
                "suggested_energy_type": mapped_energy,
            }

    return {
        "high_energy_decision": False,
        "high_energy_source": "rule_evidence_gate",
        "high_energy_confidence": 0.85,
        "high_energy_evidence": [],
        "suggested_energy_type": "low-energy/ergonomic",
    }


def classify_energy(
    raw_text: str,
    preprocessed_text: Optional[str] = None,
    hazard_category: Optional[str] = None,
    model_name: Optional[str] = None,
) -> dict[str, Any]:
    """Classify energy type with rule-gated high energy decision.
    
    Returns both the descriptive energy_type classification and the authoritative
    high_energy_decision driven by physical evidence.
    """
    target_text = preprocessed_text or raw_text

    # 1. Rule/evidence-based high-energy gate
    gate_res = evaluate_high_energy_gate(raw_text, hazard_category=hazard_category)

    # 2. Descriptive energy classification (model inference if available)
    model_prediction = None
    try:
        from sif_engine.inference.model_registry import get_model, get_active_model
        model = get_model(model_name) if model_name else get_active_model()
        if model is not None:
            pred = model.predict(target_text)
            predicted_lsr = pred.get("lsr_tag", "Work Authorisation")
            mapped_energy = LSR_TO_ENERGY_MAP.get(predicted_lsr, "stored/electrical energy")
            model_prediction = {
                "label": mapped_energy,
                "confidence": round(float(pred.get("confidence", 0.85)), 3),
                "lsr_tag": predicted_lsr,
                "model_version": pred.get("model_version", "baseline2-v0.3"),
            }
    except Exception:
        model_prediction = None

    if model_prediction:
        descriptive_label = model_prediction["label"]
        descriptive_conf = model_prediction["confidence"]
        source = "model"
        lsr_tag = model_prediction["lsr_tag"]
        model_ver = model_prediction["model_version"]
    elif hazard_category and hazard_category in HAZARD_TO_ENERGY_MAP:
        descriptive_label = HAZARD_TO_ENERGY_MAP[hazard_category]
        descriptive_conf = 0.65
        source = "fallback"
        meta = ENERGY_TYPE_METADATA.get(descriptive_label, {"lsr_tag": "Other"})
        lsr_tag = meta["lsr_tag"]
        model_ver = "rule-fallback-v0.1"
    else:
        descriptive_label = gate_res["suggested_energy_type"]
        descriptive_conf = 0.55
        source = "fallback"
        meta = ENERGY_TYPE_METADATA.get(descriptive_label, {"lsr_tag": "Work Authorisation"})
        lsr_tag = meta["lsr_tag"]
        model_ver = "rule-fallback-v0.1"

    # Authoritative high energy decision comes from the evidence gate,
    # ensuring safety-critical recall is protected against statistical misclassification.
    is_high_energy = gate_res["high_energy_decision"]
    if is_high_energy and descriptive_label == "low-energy/ergonomic":
        # Override descriptive label if physical high-energy cues are indisputable
        descriptive_label = gate_res["suggested_energy_type"]
        lsr_tag = ENERGY_TYPE_METADATA.get(descriptive_label, {}).get("lsr_tag", lsr_tag)

    return {
        "label": descriptive_label,
        "confidence": descriptive_conf,
        "is_high_energy": is_high_energy,
        "source": source,
        "lsr_tag": lsr_tag,
        "model_version": model_ver,
        # Authoritative gate contract fields
        "high_energy_decision": is_high_energy,
        "high_energy_source": gate_res["high_energy_source"],
        "high_energy_confidence": gate_res["high_energy_confidence"],
        "high_energy_evidence": gate_res["high_energy_evidence"],
        "energy_type": descriptive_label,
    }


def classify_energy_type(text: str) -> tuple[str, float]:
    """Legacy backward-compatible API: returns (label, confidence)."""
    res = classify_energy(raw_text=text)
    return res["label"], res["confidence"]