"""Precursor clustering over STRUCTURED EVENT FRAMES — not raw report text.

This is the distinction that makes requirement (c) work. Frequency counting on
raw text misses recurring patterns that are worded differently: "stood under
load" and "was positioned beneath the suspended pipe section" describe the same
precursor and share almost no vocabulary. Clustering the extracted frame
(activity + energy + barrier state + exposure) groups them correctly, because
by that stage the wording has already been normalised into ontology terms.

Density-based clustering (HDBSCAN) rather than k-means, for two reasons that
matter here: precursor patterns are not evenly sized and their number is not
known in advance, and HDBSCAN can legitimately label a report as noise instead
of forcing it into the nearest cluster. A forced assignment would fabricate a
pattern that does not exist, which in this domain means sending an HSE team to
investigate a mirage.

Patterns are typed on two independent axes so recurrence and severity are never
conflated into one ranked list:

    established              recurring and spread over the whole window
    emerging                 concentrated in the most recent portion
    sporadic_high_severity   too rare to "recur", but high energy with no
                             barrier — must never be suppressed for being rare
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

import numpy as np

# Weight of the free-text embedding relative to the structured categorical
# signal. Kept deliberately low: the structured frame is the trustworthy part,
# the text is a tie-breaker for sub-patterns within the same frame.
TEXT_WEIGHT = 0.35


def _parse_ts(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _clean(value: Any) -> str:
    """Normalise a field value, treating pandas NaN and the string "nan" as missing.

    CSV round-tripping turns empty cells into float NaN, and a bare str() on
    that yields the string "nan" — which then propagates all the way to the
    dashboard as a cluster labelled "LSR=nan". Centralised here so every
    consumer gets the same treatment.
    """
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in ("nan", "none", "<na>"):
        return ""
    return text


def _frame_key(frame: dict) -> str:
    """The canonical structured signature of an event frame."""
    return " | ".join([
        str(frame.get("activity") or "unknown activity"),
        str(frame.get("energy_type") or "unknown energy"),
        str(frame.get("barrier_status") or "unknown barrier"),
        str(frame.get("exposure") or "unknown exposure"),
    ])


def build_feature_matrix(event_frames: Sequence[dict], use_text: bool = True) -> np.ndarray:
    """One-hot the structured fields, optionally concatenating text embeddings."""
    from sklearn.preprocessing import OneHotEncoder

    if not event_frames:
        return np.zeros((0, 1), dtype=np.float32)

    cats = [
        [
            str(f.get("activity") or "unknown"),
            str(f.get("energy_type") or "unknown"),
            str(f.get("barrier_status") or "unknown"),
            str(f.get("exposure") or "unknown"),
            str(f.get("barrier_type") or "unknown"),
        ]
        for f in event_frames
    ]
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    structured = encoder.fit_transform(cats).astype(np.float32)
    # L2-normalise so the structured block has unit scale per row
    norms = np.clip(np.linalg.norm(structured, axis=1, keepdims=True), 1e-9, None)
    structured = structured / norms

    if not use_text:
        return structured

    texts = [str(f.get("report_text") or "") for f in event_frames]
    if not any(texts):
        return structured

    try:
        from sif_engine.extraction.embeddings import embed

        text_vecs = embed(texts)
        if text_vecs.shape[0] != structured.shape[0]:
            return structured
        return np.hstack([structured, TEXT_WEIGHT * text_vecs]).astype(np.float32)
    except Exception:
        return structured


def cluster_events(event_frames: Sequence[dict], min_cluster_size: int = 8,
                   min_samples: Optional[int] = None, use_text: bool = True) -> list[int]:
    """Cluster structured event frames. Returns a label per frame (-1 = noise)."""
    n = len(event_frames)
    if n == 0:
        return []
    if n < max(2, min_cluster_size):
        # Too few points for density clustering to mean anything — group by the
        # exact structured signature instead of inventing density structure.
        keys: dict[str, int] = {}
        return [keys.setdefault(_frame_key(f), len(keys)) for f in event_frames]

    X = build_feature_matrix(event_frames, use_text=use_text)

    try:
        from sklearn.cluster import HDBSCAN

        model = HDBSCAN(
            min_cluster_size=max(2, int(min_cluster_size)),
            min_samples=min_samples,
            metric="euclidean",
            cluster_selection_method="eom",
            copy=True,
        )
        labels = model.fit_predict(X)
    except Exception:
        from sklearn.cluster import AgglomerativeClustering

        k = max(2, min(24, n // max(1, min_cluster_size)))
        labels = AgglomerativeClustering(n_clusters=k).fit_predict(X)

    return [int(v) for v in labels]


def _pattern_summary(frames: Sequence[dict]) -> str:
    """Human-readable pattern label, built from the modal structured fields."""
    def modal(field: str, default: str) -> str:
        vals = [str(f.get(field)) for f in frames if f.get(field)]
        return Counter(vals).most_common(1)[0][0] if vals else default

    activity = modal("activity", "unspecified activity")
    energy = modal("energy_type", "unspecified energy")
    barrier_status = modal("barrier_status", "unknown")
    exposure = modal("exposure", "unknown exposure")

    barrier_text = {
        "confirmed_present": "barrier confirmed",
        "uncertain": "unverified barrier",
        "explicitly_absent": "absent barrier",
        "not_mentioned": "barrier not recorded",
    }.get(barrier_status, barrier_status)
    exposure_text = {
        "direct_proximity": "direct exposure",
        "indirect_proximity": "indirect exposure",
        "no_exposure": "no exposure",
    }.get(exposure, exposure)

    return f"{activity} + {energy} + {barrier_text} + {exposure_text}"


def _classify_pattern(frames: Sequence[dict], now: Optional[datetime],
                      recent_fraction: float = 0.25) -> str:
    """established | emerging | sporadic_high_severity."""
    high_energy = sum(1 for f in frames if f.get("is_high_energy", True))
    no_barrier = sum(
        1 for f in frames
        if str(f.get("barrier_status")) in ("explicitly_absent", "not_mentioned")
    )
    if len(frames) <= 5 and high_energy >= max(1, len(frames) - 1) and no_barrier >= 1:
        return "sporadic_high_severity"

    times = [t for t in (_parse_ts(f.get("timestamp")) for f in frames) if t]
    if len(times) >= 4 and now is not None:
        span_start, span_end = min(times), max(times)
        total = (span_end - span_start).total_seconds()
        if total > 0:
            cutoff = span_end.timestamp() - total * recent_fraction
            recent = sum(1 for t in times if t.timestamp() >= cutoff)
            # Far more mass in the recent window than uniform would predict
            if recent / len(times) >= min(0.6, recent_fraction * 2.4):
                return "emerging"
    return "established"


def build_clusters(
    event_frames: Sequence[dict],
    min_cluster_size: int = 8,
    max_edges_per_cluster: int = 40,
    use_text: bool = True,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Full clustering pass, shaped for ``GET /dashboard/clusters``.

    Returns ``{"clusters": [...], "edges": [...], "noise_count": int}``.
    Each cluster carries its member report ids, sites, dominant LSR, pattern
    type and the barrier failure mode that characterises it.
    """
    frames = list(event_frames)
    if not frames:
        return {"clusters": [], "edges": [], "noise_count": 0}

    now = now or datetime.now(timezone.utc)
    labels = cluster_events(frames, min_cluster_size=min_cluster_size, use_text=use_text)

    grouped: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        if label < 0:
            continue
        grouped.setdefault(label, []).append(idx)

    X = build_feature_matrix(frames, use_text=use_text)

    clusters: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for label, members in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        member_frames = [frames[i] for i in members]
        sites = sorted({_clean(f.get("site")) for f in member_frames if _clean(f.get("site"))})
        lsr_counts = Counter(
            str(f.get("lsr_tag")) for f in member_frames
            if _clean(f.get("lsr_tag")) not in ("", "N/A")
        )
        failure_modes = Counter(
            str(f.get("barrier_failure_mode")) for f in member_frames
            if _clean(f.get("barrier_failure_mode"))
        )
        times = [t for t in (_parse_ts(f.get("timestamp")) for f in member_frames) if t]
        sif_count = sum(1 for f in member_frames if f.get("sif_potential"))

        cluster_id = f"c{label}"
        clusters.append({
            "cluster_id": cluster_id,
            "pattern_summary": _pattern_summary(member_frames),
            "member_report_ids": [str(f.get("report_id")) for f in member_frames],
            "member_count": len(members),
            "sites": sites,
            "site_count": len(sites),
            "primary_lsr": lsr_counts.most_common(1)[0][0] if lsr_counts else "N/A",
            "primary_barrier_failure": (
                failure_modes.most_common(1)[0][0] if failure_modes else "not characterised"
            ),
            "barrier_type": (
                Counter(
                    _clean(f.get("barrier_type")) for f in member_frames
                    if _clean(f.get("barrier_type"))
                ).most_common(1)[0][0]
                if any(_clean(f.get("barrier_type")) for f in member_frames) else None
            ),
            "pattern_type": _classify_pattern(member_frames, now),
            "sif_member_count": sif_count,
            "sif_share": round(sif_count / len(members), 4),
            "mean_magnitude": round(
                float(np.mean([float(f.get("magnitude_class") or 1) for f in member_frames])), 2
            ),
            "first_seen": min(times).isoformat() if times else None,
            "last_seen": max(times).isoformat() if times else None,
        })

        # Similarity edges within the cluster, for the graph view. Capped so a
        # 300-member cluster does not emit 45,000 edges to the browser.
        if len(members) >= 2:
            sub = X[members]
            norms = np.clip(np.linalg.norm(sub, axis=1, keepdims=True), 1e-9, None)
            sims = (sub / norms) @ (sub / norms).T
            pairs: list[tuple[float, int, int]] = []
            for a in range(len(members)):
                for b in range(a + 1, len(members)):
                    pairs.append((float(sims[a, b]), a, b))
            pairs.sort(reverse=True)
            for sim, a, b in pairs[:max_edges_per_cluster]:
                edges.append({
                    "source": str(frames[members[a]].get("report_id")),
                    "target": str(frames[members[b]].get("report_id")),
                    "similarity": round(sim, 4),
                    "cluster_id": cluster_id,
                })

    return {
        "clusters": clusters,
        "edges": edges,
        "noise_count": int(sum(1 for label in labels if label < 0)),
    }


__all__ = ["cluster_events", "build_clusters", "build_feature_matrix"]
