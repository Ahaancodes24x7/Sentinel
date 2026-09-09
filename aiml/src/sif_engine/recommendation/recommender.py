"""Pattern -> ranked interventions, with a full evidence trail.

Takes a detected recurring pattern (from ``patterns/clustering.py`` and
``patterns/association_mining.py``), looks up applicable controls from the
curated ``intervention_library``, ranks them by hierarchy of controls, and
attaches the evidence that justified surfacing the pattern at all — which
reports, which sites, over what window.

Two wording rules are enforced structurally rather than left to reviewer
discipline:

* ``expected_objective`` is assembled from a fixed template. It always reads
  "Reduce recurrence of ...", never "will prevent" or "will reduce X by Y%".
  The system has observational report data, not a controlled trial, and cannot
  support an effectiveness claim.
* The evidence breakdown reports counts, never causes. "14 of 18 reports
  mention missing isolation" is a fact about the corpus; "missing isolation
  caused this pattern" is not something this data can establish.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from sif_engine.recommendation.intervention_library import get_interventions

# Priority is driven by evidence weight, not by a tuned score. Each threshold
# is stated so a reviewer can disagree with it explicitly.
PRIORITY_RULES = [
    ("HIGH", "20+ reports, or an emerging pattern with direct exposure"),
    ("MEDIUM", "8+ reports"),
    ("LOW", "fewer than 8 reports"),
]


def _parse_ts(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _title_for(pattern: dict) -> str:
    """Readable pattern title, derived from the barrier that keeps failing."""
    barrier = pattern.get("barrier_type")
    lsr = pattern.get("primary_lsr")
    if barrier and barrier != "None":
        return f"{barrier} failures"
    if lsr and lsr != "N/A":
        return f"{lsr} precursor pattern"
    return "Recurring precursor pattern"


def _priority_for(pattern: dict, member_frames: Sequence[dict]) -> str:
    count = int(pattern.get("member_count") or len(member_frames))
    pattern_type = str(pattern.get("pattern_type") or "established")
    direct = sum(1 for f in member_frames if str(f.get("exposure")) == "direct_proximity")

    if pattern_type == "sporadic_high_severity":
        return "HIGH"
    if count >= 20:
        return "HIGH"
    if pattern_type == "emerging" and direct >= max(1, count // 3):
        return "HIGH"
    if count >= 8:
        return "MEDIUM"
    return "LOW"


def _evidence_breakdown(member_frames: Sequence[dict]) -> dict[str, int]:
    """Counts only. Deliberately no causal framing."""
    breakdown: Counter = Counter()
    for f in member_frames:
        status = str(f.get("barrier_status") or "")
        if status == "explicitly_absent":
            breakdown["barrier_explicitly_absent"] += 1
        elif status == "uncertain":
            breakdown["barrier_unverified"] += 1
        elif status == "not_mentioned":
            breakdown["barrier_not_recorded"] += 1
        if str(f.get("exposure")) == "direct_proximity":
            breakdown["direct_personnel_exposure"] += 1
        if f.get("sif_potential"):
            breakdown["flagged_sif_potential"] += 1
        if int(f.get("magnitude_class") or 0) >= 4:
            breakdown["high_energy_present"] += 1
        mode = f.get("barrier_failure_mode")
        if mode:
            breakdown[f"failure_mode::{mode}"] += 1
    return dict(breakdown.most_common())


def recommend(
    pattern: dict,
    member_frames: Optional[Sequence[dict]] = None,
    window_days: int = 42,
) -> dict[str, Any]:
    """Build ranked recommendations plus an evidence trail for one pattern."""
    member_frames = list(member_frames or [])

    barrier_type = pattern.get("barrier_type")
    if not barrier_type and member_frames:
        counts = Counter(str(f.get("barrier_type")) for f in member_frames if f.get("barrier_type"))
        barrier_type = counts.most_common(1)[0][0] if counts else None
    barrier_type = barrier_type or "Permit to work"

    activity_counts = Counter(str(f.get("activity")) for f in member_frames if f.get("activity"))
    primary_activity = activity_counts.most_common(1)[0][0] if activity_counts else None

    interventions = get_interventions(barrier_type, primary_activity)

    sites = pattern.get("sites") or sorted({str(f.get("site")) for f in member_frames if f.get("site")})
    member_ids = pattern.get("member_report_ids") or [str(f.get("report_id")) for f in member_frames]

    times = [t for t in (_parse_ts(f.get("timestamp")) for f in member_frames) if t]
    observed_days = (max(times) - min(times)).days if len(times) >= 2 else window_days

    failure_modes = Counter(
        str(f.get("barrier_failure_mode")) for f in member_frames if f.get("barrier_failure_mode")
    )
    primary_failure = (
        pattern.get("primary_barrier_failure")
        or (failure_modes.most_common(1)[0][0] if failure_modes else "not characterised")
    )

    priority = _priority_for(pattern, member_frames)

    return {
        "pattern_id": str(pattern.get("cluster_id") or pattern.get("pattern_id") or "unknown"),
        "title": _title_for({**pattern, "barrier_type": barrier_type}),
        "priority": priority,
        "primary_barrier_failure": primary_failure,
        "barrier_type": barrier_type,
        "primary_activity": primary_activity,
        "primary_lsr": pattern.get("primary_lsr") or "N/A",
        "pattern_type": pattern.get("pattern_type") or "established",
        "evidence": {
            "report_count": len(member_ids),
            "site_count": len(sites),
            "sites": sites,
            "window_days": observed_days or window_days,
            "member_report_ids": member_ids[:200],
            "breakdown": _evidence_breakdown(member_frames),
            "first_seen": min(times).isoformat() if times else None,
            "last_seen": max(times).isoformat() if times else None,
        },
        "recommended_interventions": interventions,
        # Fixed template. Never an effectiveness or causal claim.
        "expected_objective": (
            f"Reduce recurrence of reports involving {primary_failure.lower()}"
            + (f" during {primary_activity}." if primary_activity else ".")
        ),
        "disclaimer": (
            "Interventions are drawn from a curated, version-controlled control library "
            "and ranked by hierarchy of controls. Evidence shown is co-occurrence in "
            "reported observations, not a demonstrated causal relationship."
        ),
    }


def recommend_all(
    clusters: Sequence[dict],
    frames_by_report_id: Optional[dict[str, dict]] = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Build the ranked Action Center list from a set of clusters."""
    frames_by_report_id = frames_by_report_id or {}
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    out: list[dict[str, Any]] = []

    for cluster in clusters:
        members = [
            frames_by_report_id[rid]
            for rid in (cluster.get("member_report_ids") or [])
            if rid in frames_by_report_id
        ]
        out.append(recommend(cluster, members))

    out.sort(key=lambda r: (order.get(r["priority"], 3), -r["evidence"]["report_count"]))
    return out[:limit]


__all__ = ["recommend", "recommend_all", "PRIORITY_RULES"]
