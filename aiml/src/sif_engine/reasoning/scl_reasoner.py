"""Implements the EEI SCL-style decision logic: given extracted fields (activity, energy_type, barrier_status, exposure), returns sif_potential: bool, lsr_tag: str, and a plain-language justification string built from the fields themselves (never a black-box score with no explanation attached). Exposes reason(fields: dict) -> dict."""

def reason(fields: dict) -> dict:
    """Apply SCL-style rules to extracted fields."""
    raise NotImplementedError