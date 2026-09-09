"""Analytics layer: DB rows -> structured event frames -> patterns and metrics.

This module is the seam between persistence and the AI/ML `sif_engine` package.
Endpoints in `main.py` stay thin: they authenticate, filter, and hand a query to
one of these functions. Nothing here reimplements pipeline logic — clustering,
association mining, trend detection and intervention lookup all live in
`sif_engine` and are called, not duplicated.

The precursor-density metric is implemented here rather than in the model layer
because it is an *operational reporting* choice (what counts as a fair
comparison between sites) rather than a model prediction, and because it must
be tunable by OIL without retraining anything.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

# Make the AI/ML package importable when running from the repo root.
_AIML_SRC = Path(__file__).resolve().parent.parent / "aiml" / "src"
if _AIML_SRC.is_dir() and str(_AIML_SRC) not in sys.path:
    sys.path.insert(0, str(_AIML_SRC))


# --------------------------------------------------------------------------
# Frame conversion
# --------------------------------------------------------------------------


def report_to_frame(report) -> dict[str, Any]:
    """Turn a ReportModel row into the structured event frame the AI/ML
    pattern layer expects."""
    ext = report.extracted_fields or {}

    def field(name: str, key: str = "label"):
        node = ext.get(name)
        if isinstance(node, dict):
            return node.get(key) or node.get("text")
        return node

    return {
        "report_id": report.report_id,
        "site": report.site,
        "timestamp": report.timestamp.isoformat() if report.timestamp else None,
        "activity": report.activity or field("activity", "text"),
        "energy_type": report.energy_type or field("energy_type"),
        "barrier_type": report.barrier_type,
        "barrier_status": report.barrier_status or field("barrier_status"),
        "barrier_failure_mode": report.barrier_failure_mode,
        "exposure": report.exposure or field("exposure"),
        "magnitude_class": report.magnitude_class or 1,
        "is_high_energy": bool(report.is_high_energy),
        "sif_potential": bool(report.sif_potential),
        "lsr_tag": report.lsr_tag,
        "report_text": report.report_text,
        "confidence": report.confidence,
    }


def frames_from(reports: Iterable) -> list[dict[str, Any]]:
    return [report_to_frame(r) for r in reports]


# --------------------------------------------------------------------------
# Clustering
# --------------------------------------------------------------------------


def compute_clusters(frames: list[dict], min_cluster_size: int = 15,
                     use_text: bool = False) -> dict[str, Any]:
    """Run the batch clustering job over structured frames.

    ``use_text`` defaults to False for the batch job: sentence-transformer
    embeddings over 10k+ reports cost minutes, and the structured frame already
    carries the signal that matters. It can be switched on for smaller,
    focused analyses where sub-pattern separation is worth the time.
    """
    from sif_engine.patterns.clustering import build_clusters

    return build_clusters(
        frames,
        min_cluster_size=min_cluster_size,
        use_text=use_text,
        now=datetime.now(timezone.utc),
    )


def compute_associations(frames: list[dict], min_support: float = 0.004,
                         min_confidence: float = 0.5, min_lift: float = 1.3,
                         top_n: int = 25) -> list[dict[str, Any]]:
    from sif_engine.patterns.association_mining import mine_associations

    return mine_associations(
        frames, min_support=min_support, min_confidence=min_confidence,
        min_lift=min_lift, top_n=top_n,
    )


def compute_barrier_failures(frames: list[dict], min_count: int = 5) -> list[dict[str, Any]]:
    from sif_engine.patterns.association_mining import mine_barrier_failure_pairs

    return mine_barrier_failure_pairs(frames, min_count=min_count)


def compute_trends(frames: list[dict], granularity: str = "weekly") -> dict[str, Any]:
    from sif_engine.patterns.trend_detection import analyse

    return analyse(frames, granularity=granularity)


# --------------------------------------------------------------------------
# Precursor-density metric
# --------------------------------------------------------------------------


def _ontology_weights() -> dict[str, float]:
    try:
        from sif_engine.data_generation.ontology import DENSITY_METRIC

        return DENSITY_METRIC.get("weights", {})
    except Exception:
        return {}


def _site_workforce() -> dict[str, dict]:
    try:
        from sif_engine.data_generation.ontology import SITES

        return {s["name"]: s for s in SITES}
    except Exception:
        return {}


def compute_density(
    frames: list[dict],
    group_by: str = "site",
    metric: str = "simple",
    window_days: int = 42,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Rank sites or activities by SIF-precursor density.

    ``simple``    PSIF-flagged / total reports. Transparent, and biased by
                  reporting culture — a site that reports well looks worse.

    ``composite`` A documented, tunable blend of precursor rate, barrier-gap
                  severity, energy magnitude and pattern recurrence, with a
                  correction for reporting-volume-per-worker. The weights are
                  returned alongside the numbers and default to equal. They are
                  explicitly NOT calibrated — presenting an uncalibrated
                  composite as if it were validated is the exact failure mode
                  the blueprint calls out, so the response always carries
                  ``calibrated: false``.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    prev_cutoff = now - timedelta(days=window_days * 2)

    groups: dict[str, list[dict]] = defaultdict(list)
    prev_groups: dict[str, list[dict]] = defaultdict(list)

    for f in frames:
        key = str(f.get(group_by) or "unknown")
        ts = _parse(f.get("timestamp"))
        if ts is None:
            groups[key].append(f)
            continue
        if ts >= cutoff:
            groups[key].append(f)
        elif ts >= prev_cutoff:
            prev_groups[key].append(f)

    weights = _ontology_weights()
    workforce = _site_workforce()

    # Reporting-volume baseline: reports per worker across all sites, used to
    # damp the "good reporters look dangerous" artefact.
    per_worker = []
    for key, items in groups.items():
        rec = workforce.get(key)
        if rec and rec.get("workforce"):
            per_worker.append(len(items) / rec["workforce"])
    baseline_pw = sum(per_worker) / len(per_worker) if per_worker else 0.0

    rows: list[dict[str, Any]] = []
    for key, items in groups.items():
        total = len(items)
        if total == 0:
            continue
        flagged = [f for f in items if f.get("sif_potential")]
        n_flagged = len(flagged)
        simple = n_flagged / total

        lsr_counts = Counter(
            str(f.get("lsr_tag")) for f in flagged
            if f.get("lsr_tag") and str(f.get("lsr_tag")) not in ("N/A", "nan", "None")
        )

        prev = prev_groups.get(key, [])
        prev_flagged = sum(1 for f in prev if f.get("sif_potential"))
        if prev_flagged == 0:
            trend_pct = 100.0 if n_flagged > 0 else 0.0
        else:
            trend_pct = round((n_flagged - prev_flagged) / prev_flagged * 100.0, 1)
        trend_dir = "up" if trend_pct > 5 else ("down" if trend_pct < -5 else "flat")

        density = simple
        components: dict[str, float] = {}
        if metric == "composite":
            gap_scores = {"explicitly_absent": 1.0, "uncertain": 0.6,
                          "not_mentioned": 0.5, "confirmed_present": 0.0}
            mean_gap = (
                sum(gap_scores.get(str(f.get("barrier_status")), 0.4) for f in items) / total
            )
            mags = [float(f.get("magnitude_class") or 1) for f in flagged]
            mean_mag = (sum(mags) / len(mags) / 5.0) if mags else 0.0
            distinct_patterns = len({
                (f.get("activity"), f.get("barrier_failure_mode"))
                for f in flagged if f.get("barrier_failure_mode")
            })
            recurrence = min(1.0, distinct_patterns / 10.0)

            rec = workforce.get(key)
            culture_penalty = 0.0
            if rec and rec.get("workforce") and baseline_pw > 0:
                pw = total / rec["workforce"]
                # A site reporting far ABOVE baseline is likely reporting well,
                # not necessarily more dangerous — damp its score slightly.
                culture_penalty = max(0.0, (pw - baseline_pw) / baseline_pw) * weights.get(
                    "reporting_culture_penalty", 0.10
                )

            components = {
                "psif_rate": round(simple, 4),
                "barrier_gap": round(mean_gap, 4),
                "energy_magnitude": round(mean_mag, 4),
                "pattern_recurrence": round(recurrence, 4),
                "reporting_culture_penalty": round(culture_penalty, 4),
            }
            density = (
                weights.get("w1_psif_rate", 0.25) * simple
                + weights.get("w4_barrier_gap", 0.25) * mean_gap
                + weights.get("w3_energy_magnitude", 0.25) * mean_mag
                + weights.get("w2_pattern_recurrence", 0.25) * recurrence
                - culture_penalty
            )
            density = max(0.0, min(1.0, density))

        rows.append({
            "group": key,
            "sif_flagged_count": n_flagged,
            "total_reports": total,
            "density": round(density, 4),
            "simple_density": round(simple, 4),
            "trend_direction": trend_dir,
            "trend_pct": float(trend_pct),
            "primary_lsr": lsr_counts.most_common(1)[0][0] if lsr_counts else "N/A",
            "components": components,
        })

    rows.sort(key=lambda r: -r["density"])
    return {
        "metric": metric,
        "window_days": window_days,
        "group_by": group_by,
        "rankings": rows,
        "weights": weights if metric == "composite" else None,
        "calibrated": False,
        "note": (
            "Weights default to equal and are tunable. To be calibrated jointly "
            "with OIL HSE SMEs against historical intervention outcomes."
            if metric == "composite" else
            "Simple ratio of SIF-flagged reports to total reports. Transparent, "
            "but biased by differences in reporting culture between sites."
        ),
    }


# --------------------------------------------------------------------------
# Recommendations
# --------------------------------------------------------------------------


def build_recommendations(clusters: list[dict], frames: list[dict],
                          limit: int = 20) -> list[dict[str, Any]]:
    from sif_engine.recommendation.recommender import recommend_all

    by_id = {str(f["report_id"]): f for f in frames}
    return recommend_all(clusters, by_id, limit=limit)


def build_recommendation_detail(cluster: dict, frames: list[dict]) -> dict[str, Any]:
    from sif_engine.recommendation.recommender import recommend

    ids = set(cluster.get("member_report_ids") or [])
    members = [f for f in frames if str(f.get("report_id")) in ids]
    return recommend(cluster, members)


# --------------------------------------------------------------------------


def _parse(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


__all__ = [
    "report_to_frame",
    "frames_from",
    "compute_clusters",
    "compute_associations",
    "compute_barrier_failures",
    "compute_trends",
    "compute_density",
    "build_recommendations",
    "build_recommendation_detail",
]
