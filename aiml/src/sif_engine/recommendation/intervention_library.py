"""Curated, version-controlled barrier -> control -> intervention lookup table, organized by hierarchy of controls (engineering > administrative > procedural > training). This is a config-driven lookup, NOT LLM-generated free text. Exposes get_interventions(barrier_type: str, activity: str) -> list[dict], each with control_level and priority."""

def get_interventions(barrier_type: str, activity: str) -> list[dict]:
    """Look up curated interventions for a barrier and activity."""
    raise NotImplementedError