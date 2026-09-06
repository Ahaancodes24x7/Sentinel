"""HDBSCAN clustering over embedded structured event frames (not raw text) to group recurring precursor patterns despite differently-worded reports. Exposes cluster_events(event_frames: list[dict]) -> list[int] (cluster labels)."""

def cluster_events(event_frames: list[dict]) -> list[int]:
    """Cluster structured event frames."""
    raise NotImplementedError