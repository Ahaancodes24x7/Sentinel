"""Given a detected recurring pattern (from patterns/clustering.py + association_mining.py) plus its evidence (report count, site count, date range), looks up applicable interventions from intervention_library.py, ranks them by hierarchy of controls, and attaches the evidence trail (which reports, which sites) to each recommendation. Exposes recommend(pattern: dict) -> dict with keys: interventions (ranked list), evidence, expected_objective (worded as 'reduce recurrence of X', never a causal effectiveness claim)."""

def recommend(pattern: dict) -> dict:
    """Build ranked recommendations with an evidence trail."""
    raise NotImplementedError