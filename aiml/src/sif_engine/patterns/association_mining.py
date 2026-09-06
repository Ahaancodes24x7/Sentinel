"""Apriori/FP-Growth (mlxtend) over (activity, energy_type, barrier_status, site) tuples to surface co-occurring combinations that are individually unremarkable but jointly dangerous. Exposes mine_associations(event_frames: list[dict], min_support: float) -> pd.DataFrame."""

def mine_associations(event_frames: list[dict], min_support: float):
    """Mine frequent structured event associations."""
    raise NotImplementedError