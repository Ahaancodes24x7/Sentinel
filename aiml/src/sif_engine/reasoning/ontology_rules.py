"""Loads configs/ontology.yaml and exposes energy_type_to_lsr(energy_type: str) -> str and is_high_energy(energy_type: str) -> bool, replacing the hardcoded ENERGY_TYPES dict from the synthetic generator with a config-driven version so Backend and AI/ML share one taxonomy file."""

from sif_engine.data_generation.ontology import high_energy, lsr_for

def energy_type_to_lsr(energy_type: str) -> str:
    """Return the configured LSR tag for an energy type."""
    return lsr_for(energy_type)

def is_high_energy(energy_type: str) -> bool:
    """Return whether the configured energy type is high energy."""
    return high_energy(energy_type)