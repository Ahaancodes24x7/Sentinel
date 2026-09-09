"""Probability calibration and calibration measurement.

Why this exists: the whole 4-bucket human-in-the-loop routing (Section 13 of
the research blueprint) is only meaningful if the confidence score means what
it says. A model whose "0.9" is right 60% of the time will send the wrong
reports to the priority queue no matter how good its ranking is. Ranking
quality (PR-AUC) and calibration quality (ECE) are different properties and
must be measured separately.

Provides:
  * :func:`calibrate`             — Platt (sigmoid) or isotonic wrapper
  * :func:`expected_calibration_error` — ECE with equal-width bins
  * :func:`reliability_curve`     — per-bin data for the dashboard chart
  * :func:`pick_threshold_for_recall` — choose an operating point by REQUIRED
    recall rather than by accuracy, which is the correct safety-domain choice
  * :func:`f_beta`                — F2 by default (recall weighted 2x), the
    metric the VelocityEHS PSIF paper tuned on
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np


def calibrate(base_model, X_train, y_train, method: str = "sigmoid", cv: int = 3):
    """Fit and return a calibrated classifier wrapping ``base_model``.

    ``method="sigmoid"`` is Platt scaling — the right default for small
    positive counts. ``method="isotonic"`` is non-parametric and stronger with
    plenty of data, but overfits when positives are scarce.
    """
    from sklearn.calibration import CalibratedClassifierCV

    y_train = np.asarray(y_train)
    n_pos = int((y_train == 1).sum())
    n_neg = int((y_train == 0).sum())
    # CalibratedClassifierCV needs at least `cv` members of each class.
    safe_cv = max(2, min(cv, n_pos, n_neg))
    if n_pos < 2 or n_neg < 2:
        raise ValueError(
            f"Cannot calibrate: need >=2 samples of each class, got pos={n_pos} neg={n_neg}"
        )

    calibrated = CalibratedClassifierCV(base_model, method=method, cv=safe_cv)
    calibrated.fit(X_train, y_train)
    return calibrated


def expected_calibration_error(y_true, y_prob, n_bins: int = 10) -> float:
    """ECE: mean |confidence - accuracy| weighted by bin population.

    0.0 is perfect. Below ~0.05 is generally considered well calibrated.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    if y_true.size == 0:
        return 0.0

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (y_prob > lo) & (y_prob <= hi) if i > 0 else (y_prob >= lo) & (y_prob <= hi)
        count = int(mask.sum())
        if count == 0:
            continue
        acc = float(y_true[mask].mean())
        conf = float(y_prob[mask].mean())
        ece += (count / n) * abs(acc - conf)
    return float(ece)


def reliability_curve(y_true, y_prob, n_bins: int = 10) -> list[dict[str, Any]]:
    """Per-bin reliability data, ready for the calibration chart on the
    Model Performance screen."""
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    out: list[dict[str, Any]] = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (y_prob > lo) & (y_prob <= hi) if i > 0 else (y_prob >= lo) & (y_prob <= hi)
        count = int(mask.sum())
        out.append({
            "bin_lower": round(float(lo), 3),
            "bin_upper": round(float(hi), 3),
            "count": count,
            "mean_confidence": round(float(y_prob[mask].mean()), 4) if count else None,
            "observed_accuracy": round(float(y_true[mask].mean()), 4) if count else None,
        })
    return out


def f_beta(precision: float, recall: float, beta: float = 2.0) -> float:
    """F-beta. beta=2 weights recall 2x precision — a missed SIF precursor is
    categorically worse than an extra human review."""
    if precision <= 0 and recall <= 0:
        return 0.0
    b2 = beta * beta
    denom = (b2 * precision) + recall
    if denom <= 0:
        return 0.0
    return float((1 + b2) * precision * recall / denom)


def pick_threshold_for_recall(y_true, y_prob, target_recall: float = 0.90) -> dict[str, float]:
    """Pick the highest threshold that still achieves ``target_recall``.

    This is the safety-domain-correct way to set an operating point: state the
    recall you must not fall below, then accept whatever review-queue size that
    implies — rather than picking a threshold that maximises accuracy and
    discovering later that it silently drops true precursors.

    Returns the threshold plus the precision/recall/F2 and, importantly, the
    ``review_queue_fraction`` it costs, so the trade-off is stated not hidden.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)
    n = len(y_true)
    total_pos = int(y_true.sum())
    if n == 0 or total_pos == 0:
        return {"threshold": 0.5, "recall": 0.0, "precision": 0.0,
                "f2": 0.0, "review_queue_fraction": 0.0}

    best = {"threshold": 0.0, "recall": 1.0, "precision": total_pos / n,
            "f2": 0.0, "review_queue_fraction": 1.0}
    for thr in np.unique(np.round(y_prob, 4)):
        pred = (y_prob >= thr).astype(int)
        tp = int(((pred == 1) & (y_true == 1)).sum())
        fp = int(((pred == 1) & (y_true == 0)).sum())
        recall = tp / total_pos
        if recall < target_recall:
            continue
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        cand = {
            "threshold": float(thr),
            "recall": float(recall),
            "precision": float(precision),
            "f2": f_beta(precision, recall, 2.0),
            "review_queue_fraction": float(pred.mean()),
        }
        # Highest threshold meeting the recall floor = smallest review queue.
        if cand["threshold"] >= best["threshold"]:
            best = cand
    return best


def summarise(y_true, y_prob, target_recall: float = 0.90,
              n_bins: int = 10) -> dict[str, Any]:
    """One-call calibration + operating-point report for the eval pipeline."""
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)
    op = pick_threshold_for_recall(y_true, y_prob, target_recall)
    result: dict[str, Any] = {
        "ece": round(expected_calibration_error(y_true, y_prob, n_bins), 4),
        "brier": round(float(brier_score_loss(y_true, y_prob)), 4),
        "pr_auc": round(float(average_precision_score(y_true, y_prob)), 4),
        "operating_point": {k: (round(v, 4) if isinstance(v, float) else v)
                            for k, v in op.items()},
        "target_recall": target_recall,
        "reliability": reliability_curve(y_true, y_prob, n_bins),
    }
    try:
        result["roc_auc"] = round(float(roc_auc_score(y_true, y_prob)), 4)
    except ValueError:
        result["roc_auc"] = None
    return result


__all__ = [
    "calibrate",
    "expected_calibration_error",
    "reliability_curve",
    "pick_threshold_for_recall",
    "f_beta",
    "summarise",
]
