"""4-bucket routing: HIGH_CONF_SIF, LOW_CONF_REVIEW, HIGH_CONF_NON_SIF, NEEDS_MORE_INFO. Exposes route(probability: float, prediction: int) -> str, with thresholds read from configs/model_config.yaml, not hardcoded."""

def route(probability: float, prediction: int) -> str:
    """Route a prediction using configured confidence thresholds."""
    raise NotImplementedError