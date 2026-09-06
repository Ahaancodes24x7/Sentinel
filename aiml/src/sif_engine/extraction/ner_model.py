"""Fine-tuned token-classification model (DistilBERT/IndicBERT via HuggingFace AutoModelForTokenClassification) for extracting activity/hazard/location spans from report text. Exposes extract_spans(text: str) -> dict."""

def extract_spans(text: str) -> dict:
    """Extract activity, hazard, and location spans from report text."""
    raise NotImplementedError