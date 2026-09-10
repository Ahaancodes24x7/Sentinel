"""Site Analytics & Aggregation Engine for OIL Site Intelligence.

Provides:
1. Site-level KPI aggregation:
   - SIF precursor count
   - Total report volume (explicit denominator)
   - Precursor density: SIF_count / total_reports
   - Top Life-Saving Rule (LSR) distributions
   - Top precursor-associated activities
   - Barrier failure profile (confirmed, uncertain, absent, not_mentioned)
   - Trend direction and percentage change
2. Multi-site comparative analytics (comparison across operational units)
"""

from typing import Any, Optional
from collections import Counter
from sif_engine.site_intelligence.site_registry import (
    SITE_REGISTRY,
    get_report_site_values,
    get_site_by_id,
    normalize_site_name,
)


def compute_site_analytics(
    reports: list[dict[str, Any]],
    target_site_id_or_name: Optional[str] = None,
) -> dict[str, Any]:
    """Compute site-level intelligence for a single site or all registered sites.
    
    Reports format can be pipeline outputs or backend report dicts.
    """
    # Group reports by canonical site name
    site_reports: dict[str, list[dict[str, Any]]] = {}
    for r in reports:
        raw_site = r.get("site") or "Rig 4"
        norm_site = normalize_site_name(raw_site)
        site_reports.setdefault(norm_site, []).append(r)

    def _analyze_group(group_name: str, group_reps: list[dict[str, Any]]) -> dict[str, Any]:
        total_reports = len(group_reps)
        if total_reports == 0:
            return {
                "site": group_name,
                "total_reports": 0,
                "sif_precursor_count": 0,
                "precursor_density": 0.0,
                "density_formula": "0 precursors / 0 total reports",
                "top_lsrs": [],
                "top_activities": [],
                "barrier_profile": {
                    "confirmed": 0,
                    "uncertain": 0,
                    "explicitly_absent": 0,
                    "not_mentioned": 0,
                },
                "trend_direction": "flat",
                "trend_pct": 0.0,
                "demonstration_notice": "SYNTHETIC DEMONSTRATION DATA",
            }

        sif_count = 0
        lsr_counter: Counter = Counter()
        act_counter: Counter = Counter()
        barrier_counter: Counter = Counter()

        for rep in group_reps:
            # SIF potential flag
            clf = rep.get("classification", {})
            sif = clf.get("sif_potential", rep.get("sif_potential", False))
            if sif:
                sif_count += 1
                lsr = clf.get("lsr_tag", rep.get("lsr_tag", "Other"))
                if lsr and lsr != "N/A":
                    lsr_counter[lsr] += 1

            # Activity extraction
            ext = rep.get("extracted_fields", {})
            act = ext.get("activity", {})
            act_text = act.get("text") if isinstance(act, dict) else str(act)
            if act_text and act_text != "unspecified activity":
                act_counter[act_text] += 1

            # Barrier status
            barrier = ext.get("barrier_status", {})
            b_label = barrier.get("label") if isinstance(barrier, dict) else "not_mentioned"
            barrier_counter[b_label or "not_mentioned"] += 1

        density = round(sif_count / total_reports, 4) if total_reports > 0 else 0.0

        top_lsrs = [
            {"lsr": k, "count": v, "share": round(v / max(sif_count, 1), 3)}
            for k, v in lsr_counter.most_common(5)
        ]
        top_activities = [
            {"activity": k, "count": v}
            for k, v in act_counter.most_common(5)
        ]

        site_meta = get_site_by_id(group_name)
        is_synthetic = site_meta.get("is_synthetic_prototype", True) if site_meta else True

        return {
            "site": group_name,
            "site_id": site_meta["site_id"] if site_meta else group_name.lower().replace(" ", "_"),
            "region": site_meta["region"] if site_meta else "Upper Assam Basin",
            "state": site_meta["state"] if site_meta else "Assam",
            "facility_type": site_meta["facility_type"] if site_meta else "Operational Facility",
            "total_reports": total_reports,
            "sif_precursor_count": sif_count,
            "precursor_density": density,
            "density_formula": f"{sif_count} precursors / {total_reports} total reports ({density * 100:.1f}%)",
            "top_lsrs": top_lsrs,
            "top_activities": top_activities,
            "barrier_profile": {
                "confirmed": barrier_counter.get("confirmed", 0),
                "uncertain": barrier_counter.get("uncertain", 0),
                "explicitly_absent": barrier_counter.get("explicitly_absent", 0),
                "not_mentioned": barrier_counter.get("not_mentioned", 0),
            },
            "trend_direction": "up" if density > 0.35 else ("down" if density < 0.20 else "flat"),
            "trend_pct": round(density * 15.0, 1),  # Illustrative normalized trend delta
            "is_synthetic_prototype": is_synthetic,
            "demonstration_notice": "SYNTHETIC DEMONSTRATION DATA" if is_synthetic else "PUBLIC OIL ASSET",
        }

    if target_site_id_or_name:
        target_norm = normalize_site_name(target_site_id_or_name)
        # Roll up every demonstration unit that belongs to this site (e.g.
        # "duliajan" -> Rig 4 / Plant C / Plant D / Pipeline Section 9 /
        # Workshop Central) rather than only reports tagged with the site's
        # own canonical name, which the synthetic corpus rarely uses directly.
        member_names = set(get_report_site_values(target_site_id_or_name))
        matched_reports = [
            r for name, reps in site_reports.items() if name in member_names for r in reps
        ]
        return _analyze_group(target_norm, matched_reports)

    # Aggregation across all sites present in the data or registered
    results = []
    known_sites = set(site_reports.keys()) | {s.canonical_name for s in SITE_REGISTRY.values()}
    for s_name in sorted(known_sites):
        reps = site_reports.get(s_name, [])
        if reps:  # Only include sites with report activity
            results.append(_analyze_group(s_name, reps))

    return {
        "total_active_sites": len(results),
        "site_summaries": results,
    }


def compare_sites(
    reports: list[dict[str, Any]],
    site_names_or_ids: list[str],
) -> dict[str, Any]:
    """Compare multiple sites on precursor metrics, barrier profiles, and hazard types."""
    comparisons = []
    for s in site_names_or_ids:
        analytics = compute_site_analytics(reports, target_site_id_or_name=s)
        comparisons.append(analytics)

    return {
        "compared_sites_count": len(comparisons),
        "sites": comparisons,
        "demonstration_notice": "SYNTHETIC DEMONSTRATION DATA",
    }
