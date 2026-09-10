"""NegEx-style interpretable feature extractor for SIF-potential classification.

Built for the transformer-stage hybrid experiment (Part 3 of
SIH_26165_Transformer_Stage_LLM_Prompt.md): a dense, named, rule-based
feature vector that can be concatenated onto transformer embeddings so the
hybrid classifier does not have to relearn negation-scope barrier logic
implicitly from ~15,000 examples.

This module does not invent new domain logic — it packages the
negation-aware hazard/activity/exposure/barrier extraction already proven
out in `sif_engine.extraction.evidence_extractor` (used by B5's SCL
reasoner) into a fixed-width, sklearn-style `fit`/`transform` feature
extractor, which is the shape the classical-ML baselines (B2/B4, TF-IDF)
and this transformer experiment both expect. `evidence_extractor.py`'s
barrier-status logic is itself the product of three real bugs found only
by running extraction against the full dataset (see its module docstring
history in `train_baselines.py`'s summary section) — most relevantly, the
fuzzy-typo-correction bug that turned "not re-verified" (a real barrier
gap) into "not verified", which this feature set's negation-aware barrier
counts are specifically designed to keep catching downstream of Stage 0.

30 named dense dimensions:
  1-8   hazard_<category>_count        (8 LSR-aligned hazard keyword groups)
  9-20  activity_<category>_count      (12 activity keyword groups)
  21    exposure_direct_proximity_count
  22    exposure_indirect_proximity_count
  23    exposure_no_exposure_count
  24    exposure_contradiction_flag
  25    barrier_confirmed_count        (affirmed, non-negated confirmation words)
  26    barrier_negated_count          (negated confirmation words, e.g. "not re-verified")
  27    barrier_explicit_absence_count (e.g. "no isolation", "without a permit")
  28    barrier_uncertain_count        (e.g. "could not be confirmed", "unverified")
  29    barrier_not_mentioned_flag     (no barrier term present in the report at all)
  30    log_word_count                 (log1p of raw whitespace token count)

`fit` is a no-op (the extractor is rule-based, not learned) but is provided
so it drops into an sklearn `Pipeline`/`ColumnTransformer` unchanged, and so
callers fit-on-train / transform-on-train+test the same way every other
feature step in this project does.
"""

from __future__ import annotations

import math
import re
from typing import Iterable

import numpy as np

from sif_engine.extraction.evidence_extractor import (
    ACTIVITY_KEYWORD_GROUPS,
    CONFIRMATION_TARGETS,
    EXPLICIT_ABSENCE_PHRASES,
    EXPOSURE_KEYWORD_GROUPS,
    HAZARD_KEYWORD_GROUPS,
    NEGATION_CUES_MULTI,
    NEGATION_CUES_SINGLE,
    NO_EXPOSURE_PHRASES,
    UNCERTAINTY_PHRASES,
    BARRIER_TERMS,
    _find_phrase_spans,
)

_HAZARD_CATS = sorted(HAZARD_KEYWORD_GROUPS)
_ACTIVITY_CATS = sorted(ACTIVITY_KEYWORD_GROUPS)

FEATURE_NAMES = (
    [f"hazard_{c}_count" for c in _HAZARD_CATS]
    + [f"activity_{c}_count" for c in _ACTIVITY_CATS]
    + [
        "exposure_direct_proximity_count",
        "exposure_indirect_proximity_count",
        "exposure_no_exposure_count",
        "exposure_contradiction_flag",
        "barrier_confirmed_count",
        "barrier_negated_count",
        "barrier_explicit_absence_count",
        "barrier_uncertain_count",
        "barrier_not_mentioned_flag",
        "log_word_count",
    ]
)

assert len(FEATURE_NAMES) == 30, f"expected 30 dims, got {len(FEATURE_NAMES)}"


def _count_phrase_hits(text_lower: str, phrases: Iterable[str]) -> int:
    return sum(len(_find_phrase_spans(text_lower, p)) for p in phrases)


def _barrier_counts(raw_text: str) -> dict:
    """Negation-aware barrier confirm/negate counts, mirroring
    evidence_extractor.extract_barrier_status's logic but returning raw
    counts (not a single winning status) so the classifier sees the full
    evidence signal rather than one collapsed label."""
    raw_lower = raw_text.lower()
    words = re.findall(r"[a-zA-Z0-9']+", raw_lower)

    explicit_absence = _count_phrase_hits(raw_text, EXPLICIT_ABSENCE_PHRASES)
    uncertain = _count_phrase_hits(raw_text, UNCERTAINTY_PHRASES)

    has_any_barrier_term = any(
        re.search(r"\b" + re.escape(term) + r"\b", raw_lower) for term in BARRIER_TERMS
    )

    barrier_token_positions: list[int] = []
    for term in BARRIER_TERMS:
        for m in re.finditer(re.escape(term), raw_lower):
            barrier_token_positions.append(len(re.findall(r"[a-zA-Z0-9']+", raw_lower[: m.start()])))

    confirmed = 0
    negated = 0
    window_words = 4
    proximity_tokens = 8
    for term in CONFIRMATION_TARGETS:
        for m in re.finditer(r"\b" + re.escape(term) + r"\b", raw_lower):
            prefix_tokens = re.findall(r"[a-zA-Z0-9']+", raw_lower[: m.start()])
            tok_idx = len(prefix_tokens)
            if barrier_token_positions and not any(
                abs(tok_idx - pos) <= proximity_tokens for pos in barrier_token_positions
            ):
                continue
            window_toks = words[max(0, tok_idx - window_words) : tok_idx]
            window_bigrams = [" ".join(window_toks[j : j + 2]) for j in range(len(window_toks) - 1)]
            is_neg = any(c in window_toks for c in NEGATION_CUES_SINGLE) or any(
                c in window_bigrams for c in NEGATION_CUES_MULTI
            )
            if is_neg:
                negated += 1
            else:
                confirmed += 1

    return {
        "confirmed": confirmed,
        "negated": negated,
        "explicit_absence": explicit_absence,
        "uncertain": uncertain,
        "not_mentioned_flag": 0 if has_any_barrier_term else 1,
    }


def _exposure_counts(raw_text: str) -> dict:
    direct = _count_phrase_hits(raw_text, EXPOSURE_KEYWORD_GROUPS["direct_proximity"])
    indirect = _count_phrase_hits(raw_text, EXPOSURE_KEYWORD_GROUPS["indirect_proximity"])
    no_exp = _count_phrase_hits(raw_text, NO_EXPOSURE_PHRASES)
    contradiction = 1 if (no_exp > 0 and (direct > 0 or indirect > 0)) else 0
    return {
        "direct": direct,
        "indirect": indirect,
        "no_exposure": no_exp,
        "contradiction_flag": contradiction,
    }


def _extract_one(raw_text: str) -> np.ndarray:
    raw_text = raw_text or ""
    text_lower = raw_text.lower()

    hazard_counts = [_count_phrase_hits(raw_text, HAZARD_KEYWORD_GROUPS[c]) for c in _HAZARD_CATS]
    activity_counts = [_count_phrase_hits(raw_text, ACTIVITY_KEYWORD_GROUPS[c]) for c in _ACTIVITY_CATS]
    exp = _exposure_counts(raw_text)
    bar = _barrier_counts(raw_text)
    n_words = len(re.findall(r"[a-zA-Z0-9']+", text_lower))

    vec = hazard_counts + activity_counts + [
        exp["direct"],
        exp["indirect"],
        exp["no_exposure"],
        exp["contradiction_flag"],
        bar["confirmed"],
        bar["negated"],
        bar["explicit_absence"],
        bar["uncertain"],
        bar["not_mentioned_flag"],
        math.log1p(n_words),
    ]
    return np.asarray(vec, dtype=np.float32)


class NegExSafetyFeatureExtractor:
    """Sklearn-style transformer producing the 30-dim NegEx-style feature
    vector described in this module's docstring.

    Stateless / rule-based: `fit` exists only so this drops into a
    `Pipeline`/`ColumnTransformer` like any learned transformer would, and
    so callers can fit-on-train, transform-on-train+test as a matter of
    discipline (avoiding leakage) even though nothing is actually learned
    from the train split here.
    """

    def __init__(self) -> None:
        self.feature_names_ = list(FEATURE_NAMES)

    def fit(self, X: Iterable[str], y=None) -> "NegExSafetyFeatureExtractor":
        return self

    def transform(self, X: Iterable[str]) -> np.ndarray:
        return np.vstack([_extract_one(t) for t in X])

    def fit_transform(self, X: Iterable[str], y=None) -> np.ndarray:
        return self.fit(X, y).transform(X)

    def get_feature_names_out(self, input_features=None) -> list[str]:
        return list(self.feature_names_)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    _ROOT = Path(__file__).resolve().parents[3]
    _SRC = _ROOT / "src"
    if str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))

    import pandas as pd

    data_path = _ROOT / "data" / "synthetic" / "synthetic_uauc_reports.csv"
    df = pd.read_csv(data_path).fillna("")
    sample = df.sample(min(5, len(df)), random_state=42)

    extractor = NegExSafetyFeatureExtractor()
    extractor.fit(df.report_text)  # no-op; shown for pipeline-shape parity
    feats = extractor.transform(sample.report_text)

    for i, (_, row) in enumerate(sample.iterrows()):
        print(f"\n--- report_id={row.report_id} sif_potential={row.sif_potential} ---")
        print(row.report_text[:160].replace("\n", " ") + ("..." if len(row.report_text) > 160 else ""))
        nonzero = {
            name: float(val)
            for name, val in zip(extractor.feature_names_, feats[i])
            if val != 0
        }
        print("nonzero features:", nonzero)
