"""Shared accessors over the Sentinel safety knowledge layer (configs/ontology.yaml).

This module is the single import point for taxonomy lookups. The backend, the
reasoner and the data generator all read the same YAML through here, so the
energy-type -> Life-Saving-Rule mapping can never drift between them.
"""

from pathlib import Path
from typing import Any, Optional

import yaml

_CONFIG = Path(__file__).resolve().parents[3] / "configs" / "ontology.yaml"

with _CONFIG.open(encoding="utf-8") as _file:
    _ontology: dict[str, Any] = yaml.safe_load(_file)

VERSION: str = _ontology.get("version", "unknown")
ACTIVITIES: list[str] = _ontology["activities"]
ENERGY_TYPES: dict[str, dict] = _ontology["energy_types"]
ACTIVITY_ENERGY_MAP: dict[str, list[str]] = _ontology["activity_energy_map"]
BARRIER_TYPES: dict[str, dict] = _ontology["barrier_types"]
LIFE_SAVING_RULES: dict[str, dict] = _ontology["life_saving_rules"]
SITES: list[dict] = _ontology["sites"]
SITE_NAMES: list[str] = [s["name"] for s in SITES]
BARRIER_STATUS_OPTIONS: list[str] = _ontology["barrier_status_options"]
EXPOSURE_OPTIONS: list[str] = _ontology["exposure_options"]
GAP_SEVERITY: dict[str, Optional[float]] = _ontology["gap_severity"]
DENSITY_METRIC: dict[str, Any] = _ontology["density_metric"]

# energy_type -> the barrier type that controls it (first declared wins)
ENERGY_TO_BARRIER: dict[str, str] = {}
for _bname, _bdef in BARRIER_TYPES.items():
    for _et in _bdef["controls_energy"]:
        ENERGY_TO_BARRIER.setdefault(_et, _bname)


def high_energy(energy_type: str) -> bool:
    """Whether this energy type clears the SCL high-energy (~1500 J) bar."""
    entry = ENERGY_TYPES.get(energy_type)
    return bool(entry["is_high_energy"]) if entry else False


def lsr_for(energy_type: str) -> str:
    """Ontology lookup: energy type -> IOGP Life-Saving Rule."""
    entry = ENERGY_TYPES.get(energy_type)
    return entry["lsr_tag"] if entry else "Work Authorisation"


def magnitude_of(energy_type: str) -> int:
    """Energy magnitude class 1-5, used for severity weighting."""
    entry = ENERGY_TYPES.get(energy_type)
    return int(entry["magnitude_class"]) if entry else 1


def barrier_for(energy_type: str) -> str:
    """The safety-critical barrier that controls this energy type."""
    return ENERGY_TO_BARRIER.get(energy_type, "Permit to work")


def is_direct_control(barrier_type: str) -> bool:
    """SCL 'direct control' test: effective even under foreseeable human error."""
    entry = BARRIER_TYPES.get(barrier_type)
    return bool(entry["is_direct_control"]) if entry else False


def gap_severity_for(barrier_status: str) -> Optional[float]:
    """Graded barrier-gap severity: 0.0 / 0.6 / 1.0, or None when not mentioned."""
    return GAP_SEVERITY.get(barrier_status)


def site_record(name: str) -> Optional[dict]:
    for s in SITES:
        if s["name"].lower() == (name or "").lower():
            return s
    return None


def energy_keywords() -> dict[str, list[str]]:
    """energy_type -> surface keywords, used by the rule/weak-supervision layer."""
    return {k: v.get("keywords", []) for k, v in ENERGY_TYPES.items()}


def as_dict() -> dict[str, Any]:
    """The whole parsed ontology, for the GET /ontology endpoint."""
    return _ontology
