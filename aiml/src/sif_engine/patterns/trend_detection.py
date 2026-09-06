"""CUSUM/EWMA control-chart early-warning over weekly precursor counts per barrier-failure-type/site. Exposes detect_trend_alerts(time_series: pd.Series) -> list[dict], each alert stating 'unusual increase in reported precursor rate — investigate', never a causal/predictive claim."""

def detect_trend_alerts(time_series):
    """Detect unusual increases in precursor reporting rates."""
    raise NotImplementedError