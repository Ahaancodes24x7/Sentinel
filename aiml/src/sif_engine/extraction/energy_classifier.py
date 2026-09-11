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
# ---------------------------------------------------------------------------
# Canonical Ontology Mapping  (config-driven: configs/ontology.yaml)
#
# These tables used to be hardcoded here, which meant adding an energy type to
# the ontology silently left this classifier behind and the two disagreed about
# what "high energy" meant. They are now derived from the single shared
# taxonomy file, so the mapping can never drift between the reasoner, the
# generator and the backend.
# ---------------------------------------------------------------------------
from sif_engine.data_generation.ontology import (  # noqa: E402
    ENERGY_TYPES as _ONT_ENERGY_TYPES,
    energy_keywords as _ont_energy_keywords,
)

ENERGY_TYPE_METADATA: dict[str, dict[str, Any]] = {
    name: {"is_high_energy": bool(meta["is_high_energy"]), "lsr_tag": meta["lsr_tag"]}
    for name, meta in _ONT_ENERGY_TYPES.items()
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
    "bypassing_safety_controls": "defeated safety system",
    "pressure": "pressure/hydraulic energy",
    "chemical": "chemical/toxic exposure",
    "radiation": "radiation (NORM/radiography)",
}

# LSR -> a representative energy type. Several energy types can share one rule
# (e.g. electrical and pressure both map to Energy Isolation), so this reverse
# lookup deliberately keeps the FIRST declared member as the representative.
LSR_TO_ENERGY_MAP: dict[str, str] = {}
for _name, _meta in _ONT_ENERGY_TYPES.items():
    LSR_TO_ENERGY_MAP.setdefault(_meta["lsr_tag"], _name)

# Hand-curated high-energy cues, layered on top of the ontology keywords.
# The ontology supplies breadth; these add phrasings observed in real incident
# narratives that are too specific to live in the shared taxonomy.
_CURATED_CUES: dict[str, list[str]] = {
    "stored/electrical energy": [
        "live circuit", "live wire", "switchboard", "isolation failure",
        "high voltage", "arc flash", "power line",
    ],
    "thermal (hot work)": ["open flame", "torch", "spark ignition"],
    "gravitational (suspended load)": [
        "crane lift", "overhead lift", "hoist line", "derrick lift", "winch cable",
    ],
    "kinetic (line of fire)": [
        "high pressure line", "kickback", "whip check", "pressurized hose",
        "pinch point", "flying debris",
    ],
    "mechanical/rotating equipment": ["pinch point", "unguarded shaft", "caught between"],
    "atmospheric/asphyxiation": ["toxic gas", "asphyxiation", "inert atmosphere", "vessel purge"],
    "vehicular/motion": ["heavy vehicle", "truck reversing", "vehicle rollover", "transport collision"],
    "fall from height": ["working at height", "ladder fall", "roof edge", "manlift"],
    "pressure/hydraulic energy": ["stored pressure", "line not depressurised", "pressure test"],
    "flammable/explosive atmosphere": ["gas cloud", "vapour cloud", "hydrocarbon leak"],
    "defeated safety system": ["safety system disabled", "protection defeated", "alarm suppressed"],
    "chemical/toxic exposure": ["chemical burn", "chemical splash"],
    "radiation (NORM/radiography)": ["radiation source", "exposed source"],
}

HIGH_ENERGY_RULE_INDICATORS: dict[str, list[str]] = {}
for _et, _meta in _ONT_ENERGY_TYPES.items():
    if not _meta.get("is_high_energy"):
        continue          # the gate only fires on HIGH-energy evidence
    _cues = {str(k).lower() for k in _ont_energy_keywords().get(_et, [])}
    _cues.update(c.lower() for c in _CURATED_CUES.get(_et, []))
    # Single very generic tokens cause false positives ("guard", "pressure",
    # "chemical" appear in safe reports too); require a multi-word or
    # distinctive cue for the gate to fire.
    HIGH_ENERGY_RULE_INDICATORS[_et] = sorted(
        c for c in _cues if (" " in c or len(c) >= 6)
    )


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
                # The model's own binary verdict on THIS report, carried through
                # untouched so Stage 3 can check it against the SCL reasoner's
                # verdict rather than the two being computed in isolation and
                # never compared - see confidence/routing.py's model_signal.
                "sif_signal": {
                    "sif_potential": bool(pred.get("sif_potential", False)),
                    "confidence": round(float(pred.get("confidence", 0.5)), 3),
                    "model_version": pred.get("model_version", "baseline2-v0.3"),
                },
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
        # None when no model ran at all (import failed, no active model) -
        # distinct from a model that ran and predicted non-SIF, which Stage 3
        # must be able to tell apart from "no signal available".
        "sif_signal": model_prediction["sif_signal"] if model_prediction else None,
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