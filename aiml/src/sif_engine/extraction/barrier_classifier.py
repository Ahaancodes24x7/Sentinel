"""3-class classifier: barrier status is confirmed_present / uncertain / absent_not_mentioned. Exposes classify_barrier_status(text: str) -> tuple[str, float]."""

def classify_barrier_status(text: str) -> tuple[str, float]:
    """Classify barrier status in report text."""
    raise NotImplementedError