"""Synthetic-data ontology, loaded from the shared YAML configuration."""

from pathlib import Path
import yaml

_CONFIG = Path(__file__).parents[3] / "configs" / "ontology.yaml"
with _CONFIG.open(encoding="utf-8") as _file:
    _ontology = yaml.safe_load(_file)

ACTIVITIES = _ontology["activities"]
ENERGY_TYPES = {key: (value["is_high_energy"], value["lsr_tag"]) for key, value in _ontology["energy_types"].items()}
ACTIVITY_ENERGY_MAP = _ontology["activity_energy_map"]
BARRIER_STATUS_PHRASES = _ontology["barrier_status_phrases"]
EXPOSURE_PHRASES = _ontology["exposure_phrases"]
OUTCOME_PHRASES = _ontology["outcome_phrases"]
SITES = _ontology["sites"]


def high_energy(energy_type: str) -> bool:
    return ENERGY_TYPES[energy_type][0]


def lsr_for(energy_type: str) -> str:
    return ENERGY_TYPES[energy_type][1]