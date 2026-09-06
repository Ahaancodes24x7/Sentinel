"""Keyword/rule baseline for SIF-potential classification."""

HIGH_ENERGY_KEYWORDS = ["hot work", "welding", "suspended load", "crane", "confined space", "gas test", "electrical", "isolation", "energized", "line of fire", "height", "scaffolding", "excavation", "pipeline"]
BARRIER_ABSENT_KEYWORDS = ["not clearly confirmed", "could not be located", "not mentioned", "no isolation", "no exclusion zone", "without a permit", "not re-verified", "not actively enforced", "not confirmed"]
EXPOSURE_KEYWORDS = ["within", "beneath", "inside", "directly", "arm's reach", "nearby"]


def rule_predict(text: str) -> int:
    """Return the keyword-rule SIF-potential prediction."""
    text = text.lower()
    return int(any(item in text for item in HIGH_ENERGY_KEYWORDS) and any(item in text for item in BARRIER_ABSENT_KEYWORDS) and any(item in text for item in EXPOSURE_KEYWORDS))