"""End-to-end orchestrator: takes raw report text, runs Stage 0 (preprocessing) -> Stage 1 (extraction) -> Stage 2 (reasoning) -> Stage 3 (confidence/routing), and separately exposes a batch-mode function that also runs Stage 4 (patterns) + recommendation across a set of reports. Exposes run_single(text: str) -> dict and run_batch(reports: list[dict]) -> dict."""

def run_single(text: str) -> dict:
    """Run one report through the end-to-end pipeline."""
    raise NotImplementedError

def run_batch(reports: list[dict]) -> dict:
    """Run a batch of reports through the end-to-end pipeline."""
    raise NotImplementedError