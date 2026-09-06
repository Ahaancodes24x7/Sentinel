"""Multi-class classifier over the fixed energy-type taxonomy defined in configs/ontology.yaml. Exposes classify_energy_type(text: str) -> tuple[str, float] (label, confidence)."""

def classify_energy_type(text: str) -> tuple[str, float]:
    """Classify the report's energy type."""
    raise NotImplementedError