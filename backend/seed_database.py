"""Seed the Sentinel database from the synthetic UA/UC corpus.

    python -m backend.seed_database --limit 8000

Runs every report through the real Stage 0-3 pipeline (the same code path the
live ingest endpoint uses — nothing is faked or pre-baked), persists the
structured event frame, then runs the batch clustering job so the dashboard has
patterns to show on first load.

The observation timestamp from the corpus is preserved. That matters more than
it sounds: stamping rows with import time would collapse a 12-month history
into a single spike and make the trend and early-warning views meaningless.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for extra in (str(_ROOT), str(_ROOT / "aiml" / "src")):
    if extra not in sys.path:
        sys.path.insert(0, extra)

DEFAULT_CSV = _ROOT / "aiml" / "data" / "synthetic" / "synthetic_uauc_reports.csv"

GROUND_TRUTH_COLUMNS = [
    "activity", "energy_type", "barrier_type", "barrier_status",
    "barrier_failure_mode", "exposure", "magnitude_class",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(DEFAULT_CSV))
    ap.add_argument("--limit", type=int, default=0, help="0 = all rows")
    ap.add_argument("--batch-size", type=int, default=500)
    ap.add_argument("--reset", action="store_true", help="drop existing rows first")
    ap.add_argument("--skip-clusters", action="store_true")
    ap.add_argument("--min-cluster-size", type=int, default=15)
    args = ap.parse_args()

    import pandas as pd

    from backend.database import (
        AuditLogModel,
        BatchTrackerModel,
        PrecursorClusterModel,
        ReportModel,
        ReviewActionModel,
        SessionLocal,
        init_db,
    )
    from backend.main import _process_batch_ingestion, _recompute_clusters

    print("Initialising schema...")
    init_db()

    db = SessionLocal()
    try:
        if args.reset:
            print("Resetting existing data...")
            for model in (ReviewActionModel, PrecursorClusterModel,
                          AuditLogModel, BatchTrackerModel, ReportModel):
                db.query(model).delete()
            db.commit()

        existing = db.query(ReportModel).count()
        if existing and not args.reset:
            print(f"Database already holds {existing:,} reports. Use --reset to reload.")
            return

        print(f"Loading {args.csv}")
        df = pd.read_csv(args.csv).fillna("")
        if args.limit:
            df = df.head(args.limit)
        print(f"  {len(df):,} reports to ingest")

        batch_id = f"seed_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        db.add(BatchTrackerModel(
            batch_id=batch_id, total=len(df), classified=0, status="processing",
        ))
        db.commit()

        t0 = time.time()
        done = 0
        for start in range(0, len(df), args.batch_size):
            chunk = df.iloc[start:start + args.batch_size]
            payload = []
            for _, row in chunk.iterrows():
                ground_truth = {
                    col: (int(row[col]) if col == "magnitude_class" and row[col] != ""
                          else row[col])
                    for col in GROUND_TRUTH_COLUMNS
                    if col in row and row[col] != ""
                }
                payload.append({
                    "report_id": str(row["report_id"]),
                    "site": str(row["site"]),
                    "report_text": str(row["report_text"]),
                    "source": str(row.get("source") or "synthetic"),
                    "timestamp": str(row["timestamp"]) if row.get("timestamp") else None,
                    "reporter_role": str(row.get("reporter_role") or "") or None,
                    "ground_truth": ground_truth,
                })

            # Same worker the live /reports/ingest endpoint uses.
            _process_batch_ingestion(batch_id, payload)
            done += len(payload)
            rate = done / max(1e-6, time.time() - t0)
            eta = (len(df) - done) / rate if rate else 0
            print(f"  {done:,}/{len(df):,}  {rate:.0f} reports/s  ETA {eta / 60:.1f}m",
                  flush=True)

        tracker = db.query(BatchTrackerModel).filter(
            BatchTrackerModel.batch_id == batch_id
        ).first()
        if tracker:
            tracker.classified = done
            tracker.status = "complete"
            db.commit()

        total = db.query(ReportModel).count()
        flagged = db.query(ReportModel).filter(ReportModel.sif_potential == True).count()  # noqa: E712
        print(f"\nIngested {total:,} reports in {(time.time() - t0) / 60:.1f} min")
        print(f"  SIF-flagged: {flagged:,} ({flagged / max(total, 1):.1%})")

        if not args.skip_clusters:
            print("Running batch clustering job...")
            t1 = time.time()
            n = _recompute_clusters(db, min_cluster_size=args.min_cluster_size)
            print(f"  {n} precursor clusters written in {time.time() - t1:.0f}s")

        print("\nSeed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
