"""Standalone B5 (hybrid extraction + SCL reasoner) synthetic regression
check, factored out of train_models.py's B5 block so it can be run on its
own — without retraining B1-B4, the LSR/energy/barrier heads, or touching
any committed model artifact — whenever a change to extraction/reasoning
code needs a quick "did this move the synthetic-domain needle" answer.

Same sample every time: the identical stratified 60/20/20 split
(random_state=42) and 1500-report test-split sample (random_state=42) that
train_models.py's B5 block uses, so results are directly comparable across
runs and across sessions.

Origin: written for the Week 1 external-evaluation follow-up (Phase 8,
reports/WEEK1_VALIDATION_REPORT.md addendum) to verify that phrase-list
fixes aimed at the external corpus didn't regress synthetic-domain
performance, without waiting on a full train_models.py run.

Run:  python scripts/check_b5_regression.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sif_engine.pipeline import run_single  # noqa: E402
from sif_engine.preprocessing import preprocess_report  # noqa: E402

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "synthetic_uauc_reports.csv"


def main() -> None:
    df = pd.read_csv(DATA_PATH, keep_default_na=False, na_values=[])
    df["text_proc"] = [preprocess_report(t) for t in df.report_text]

    train_df, temp_df = train_test_split(df, test_size=0.4, random_state=42, stratify=df.sif_potential)
    _val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42, stratify=temp_df.sif_potential)
    sample = test_df.sample(min(1500, len(test_df)), random_state=42)

    tp = fp = fn = tn = 0
    buckets: dict[str, int] = {}
    t0 = time.time()
    for _, row in sample.iterrows():
        out = run_single(str(row.report_id), str(row.report_text), site=str(row.site))
        pred = bool(out["classification"]["sif_potential"])
        gold = bool(row.sif_potential)
        b = out["classification"]["bucket"]
        buckets[b] = buckets.get(b, 0) + 1
        if gold and pred:
            tp += 1
        elif gold and not pred:
            fn += 1
        elif not gold and pred:
            fp += 1
        else:
            tn += 1
    elapsed = time.time() - t0

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    print(f"tp={tp} fp={fp} fn={fn} tn={tn}")
    print(f"precision={precision:.4f} recall={recall:.4f} f1={f1:.4f}")
    print(f"buckets={buckets}")
    print(f"elapsed={elapsed:.1f}s ({elapsed / len(sample) * 1000:.1f}ms/report)")


if __name__ == "__main__":
    main()
