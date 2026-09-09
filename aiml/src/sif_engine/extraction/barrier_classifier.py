"""Barrier/control status classifier — 4 states with graded gap severity.

    confirmed_present  -> gap_severity 0.0
    uncertain          -> gap_severity 0.6
    explicitly_absent  -> gap_severity 1.0
    not_mentioned      -> gap_severity None  (insufficient information)

The fourth state matters and is easy to get wrong: a report that simply never
mentions a barrier is NOT evidence that the barrier was present. Collapsing
"not mentioned" into "absent" overstates the hazard; collapsing it into
"present" hides it. Keeping it separate is what lets the router send those
reports to NEEDS_MORE_INFO instead of inventing a decision — and it doubles as
a report-quality signal back to the people writing the reports.

A calibrated TF-IDF + logistic-regression model is used when a trained
artefact is available; otherwise the module falls back to the deterministic
rule layer in ``evidence_extractor``. ``classify_barrier_status`` always
reports which path produced the answer.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Optional

BARRIER_STATES = ["confirmed_present", "uncertain", "explicitly_absent", "not_mentioned"]

GAP_SEVERITY: dict[str, Optional[float]] = {
    "confirmed_present": 0.0,
    "uncertain": 0.6,
    "explicitly_absent": 1.0,
    "not_mentioned": None,
}

_MODEL_PATH = Path(__file__).resolve().parents[3] / "models" / "barrier" / "barrier_status_clf.pkl"

_model = None
_load_attempted = False
_lock = threading.Lock()


def _load_model():
    global _model, _load_attempted
    if _load_attempted:
        return _model
    with _lock:
        if _load_attempted:
            return _model
        _load_attempted = True
        try:
            import joblib

            if _MODEL_PATH.is_file():
                _model = joblib.load(_MODEL_PATH)
        except Exception:
            _model = None
    return _model


def model_available() -> bool:
    return _load_model() is not None


def _rule_status(text: str) -> tuple[str, float]:
    """Deterministic fallback via the shared evidence-extraction rule layer."""
    try:
        from sif_engine.extraction.evidence_extractor import extract_barrier_status

        result = extract_barrier_status(text)
        status = getattr(result, "status", None) or "not_mentioned"
        # evidence_extractor uses "confirmed"; normalise to the 4-state vocab
        status = {"confirmed": "confirmed_present"}.get(status, status)
        if status not in BARRIER_STATES:
            status = "not_mentioned"
        confidence = 0.72 if status != "not_mentioned" else 0.55
        return status, confidence
    except Exception:
        return "not_mentioned", 0.50


def classify_barrier_status(text: str) -> tuple[str, float]:
    """Return ``(status, confidence)`` for the barrier described in ``text``."""
    status, confidence, _ = classify_barrier_status_detailed(text)
    return status, confidence


def classify_barrier_status_detailed(text: str) -> tuple[str, float, dict[str, Any]]:
    """As above, plus a detail dict: source, full probability vector and the
    gap severity implied by the predicted state."""
    text = (text or "").strip()
    if not text:
        return "not_mentioned", 0.50, {
            "source": "empty_input",
            "gap_severity": None,
            "probabilities": {},
        }

    model = _load_model()
    if model is not None:
        try:
            probs = model.predict_proba([text])[0]
            classes = list(model.classes_)
            best = int(max(range(len(probs)), key=lambda i: probs[i]))
            status = str(classes[best])
            return status, float(probs[best]), {
                "source": "model",
                "gap_severity": GAP_SEVERITY.get(status),
                "probabilities": {str(c): round(float(p), 4) for c, p in zip(classes, probs)},
            }
        except Exception:
            pass

    status, confidence = _rule_status(text)
    return status, confidence, {
        "source": "rule_fallback",
        "gap_severity": GAP_SEVERITY.get(status),
        "probabilities": {},
    }


def gap_severity_for(status: str) -> Optional[float]:
    return GAP_SEVERITY.get(status)


def train(texts, labels, out_path: Optional[Path] = None, calibrate_probs: bool = True):
    """Train and persist the barrier-status classifier.

    Char n-grams are included alongside word n-grams on purpose: field reports
    are full of typos (`confimed`, `isolaton`) and abbreviations, and character
    features degrade far more gracefully across those than word features do.
    """
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline

    features = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3,
                                 max_features=60000, sublinear_tf=True)),
    ])
    clf = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced")
    pipeline = Pipeline([("features", features), ("clf", clf)])
    pipeline.fit(texts, labels)

    if calibrate_probs:
        from sklearn.calibration import CalibratedClassifierCV

        calibrated = CalibratedClassifierCV(pipeline, method="sigmoid", cv=3)
        calibrated.fit(texts, labels)
        pipeline = calibrated

    path = out_path or _MODEL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, path)

    global _model, _load_attempted
    _model = pipeline
    _load_attempted = True
    return pipeline


__all__ = [
    "classify_barrier_status",
    "classify_barrier_status_detailed",
    "gap_severity_for",
    "model_available",
    "train",
    "BARRIER_STATES",
    "GAP_SEVERITY",
]
