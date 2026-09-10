"""Shared data loading + metrics for the transformer-stage experiments
(SIH_26165_Transformer_Stage_LLM_Prompt.md, Parts 1-3).

Split, preprocessing and metric definitions are copied verbatim from
`train_models.py` (the script that produced the current B1-B5 ladder in
`aiml/reports/model_evaluation_report.md`, model_version sentinel-v2.0) so
that every transformer variant is evaluated on the EXACT SAME held-out
test set and the EXACT SAME F2 formula as those baselines, not a
similarly-named but different split.

Note on the split: the task prompt that spawned this work says "test_size
=0.2" (an 80/20 split), which was accurate for an older ~3,000-row version
of this dataset (see aiml/reports/mlp_model_evaluation_report.md). The
dataset has since grown to 25,000 rows and train_models.py now uses a
stratified 60/20/20 train/val/test split instead. Per the project's own
choice (benchmark against the CURRENT B1-B5 ladder, not the stale table),
this module reproduces THAT split exactly, not the literal "test_size=0.2"
instruction, so the comparison table in transformer_evaluation_report.md
is genuinely apples-to-apples with B1-B5 rather than merely similarly
sized.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sklearn.metrics import (  # noqa: E402
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split  # noqa: E402

from sif_engine.confidence.calibration import f_beta  # noqa: E402
from sif_engine.preprocessing import preprocess_report  # noqa: E402

DATA_PATH = _ROOT / "data" / "synthetic" / "synthetic_uauc_reports.csv"
MODELS_DIR = _ROOT / "models" / "transformers"
REPORTS_DIR = _ROOT / "reports"
RANDOM_STATE = 42
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def load_split() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Identical 60/20/20 stratified split + Stage-0 preprocessing to
    train_models.py, so test_df here == test_df there."""
    df = pd.read_csv(DATA_PATH).fillna("")
    df["text_proc"] = [preprocess_report(t) for t in df.report_text]

    train_df, temp_df = train_test_split(
        df, test_size=0.4, random_state=RANDOM_STATE, stratify=df.sif_potential
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.5, random_state=RANDOM_STATE, stratify=temp_df.sif_potential
    )
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True), test_df.reset_index(drop=True)


def compute_metrics(y_true, y_pred, y_prob) -> dict[str, Any]:
    """Same metric calls / F2 formula as the B1-B5 ladder, plus Brier
    score (required by this experiment, not computed by train_models.py)."""
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)

    p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    return {
        "precision": round(float(p), 4),
        "recall": round(float(r), 4),
        "f1": round(float(f1), 4),
        "f2": round(f_beta(float(p), float(r), 2.0), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "pr_auc": round(float(average_precision_score(y_true, y_prob)), 4),
        "brier": round(float(brier_score_loss(y_true, y_prob)), 4),
        "accuracy": round(float((y_true == y_pred).mean()), 4),
        "flagged_fraction": round(float(y_pred.mean()), 4),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


class Timer:
    def __init__(self, label: str):
        self.label = label

    def __enter__(self):
        self.t0 = time.time()
        print(f"[{self.label}] starting...")
        return self

    def __exit__(self, *exc):
        self.elapsed = time.time() - self.t0
        print(f"[{self.label}] done in {self.elapsed:.1f}s")


def hardware_info() -> dict[str, Any]:
    info: dict[str, Any] = {"device": "cpu"}
    try:
        import torch

        if torch.cuda.is_available():
            info["device"] = "cuda"
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["gpu_mem_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)
        info["torch_version"] = torch.__version__
    except ImportError:
        pass
    return info
