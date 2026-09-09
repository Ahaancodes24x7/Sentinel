"""Association-rule mining over structured event tuples.

Clustering tells you *which reports belong together*. Association mining tells
you *which combinations of conditions co-occur more than chance would predict*
— and it says so in a sentence an HSE reviewer can act on:

    "workover rig operation + unverified isolation co-occurs with direct
     exposure in 71% of cases, against a 24% baseline (lift = 2.9,
     34 reports)"

That is materially more useful than an opaque cluster id, which is why both
layers exist rather than one. Mining runs over ontology terms
(activity, energy_type, barrier_status, barrier_failure_mode, site, exposure),
never over raw text, so differently-worded reports contribute to the same rule.

Uses mlxtend FP-Growth when available and falls back to an exact itemset
counter for small corpora. Findings are always phrased as co-occurrence, never
causation — with only observational report data, "X causes Y" is a claim this
system has no basis to make.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any, Optional, Sequence

ITEM_FIELDS = [
    "activity",
    "energy_type",
    "barrier_status",
    "barrier_failure_mode",
    "site",
    "exposure",
]

# `lsr_tag` is deliberately EXCLUDED from the default item fields. It is a
# deterministic ontology lookup from `energy_type`, so mining it produces
# tautologies ("fall from height co-occurs with LSR Working at Height, lift
# 39") that look like discoveries but are true by construction. Surfacing
# those as findings would be the exact "impressive-looking but empty" result
# an HSE reviewer would immediately discount.
TAUTOLOGICAL_PAIRS = {("energy_type", "lsr_tag"), ("lsr_tag", "energy_type")}

# Conditions that are interesting as rule CONSEQUENTS — the things an HSE team
# actually wants predicted from the antecedent conditions.
CONSEQUENT_PREFIXES = ("exposure=", "barrier_status=", "barrier_failure_mode=")


def _to_itemset(frame: dict, fields: Sequence[str]) -> frozenset[str]:
    items: set[str] = set()
    for field in fields:
        value = frame.get(field)
        if value in (None, "", "N/A", "unknown"):
            continue
        items.add(f"{field}={value}")
    return frozenset(items)


def _phrase(item: str) -> str:
    """Turn `barrier_status=uncertain` into readable text."""
    field, _, value = item.partition("=")
    pretty = {
        "activity": "", "energy_type": "", "site": "at ",
        "barrier_status": "barrier ", "barrier_failure_mode": "",
        "lsr_tag": "LSR ", "exposure": "",
    }.get(field, "")
    value = value.replace("_", " ")
    return f"{pretty}{value}".strip()


def mine_associations(
    event_frames: Sequence[dict],
    min_support: float = 0.01,
    min_confidence: float = 0.45,
    min_lift: float = 1.25,
    max_antecedent_size: int = 3,
    fields: Optional[Sequence[str]] = None,
    top_n: int = 40,
) -> list[dict[str, Any]]:
    """Mine co-occurrence rules over structured event tuples.

    Returns rules sorted by lift, each with support/confidence/lift, the raw
    report count, and a ready-to-render plain-language statement.
    """
    frames = list(event_frames)
    n = len(frames)
    if n == 0:
        return []

    fields = list(fields or ITEM_FIELDS)
    transactions = [_to_itemset(f, fields) for f in frames]
    transactions = [t for t in transactions if t]
    n = len(transactions)
    if n == 0:
        return []

    min_count = max(2, int(min_support * n))

    # Frequent 1-itemsets
    item_counts = Counter(item for t in transactions for item in t)
    frequent_items = {i for i, c in item_counts.items() if c >= min_count}
    if not frequent_items:
        return []

    # Candidate antecedent itemsets (size 1..max_antecedent_size), counted
    # exactly. Apriori pruning keeps this tractable on a 25k corpus because the
    # vocabulary is ontology-bounded (a few hundred items, not a text vocab).
    itemset_counts: dict[frozenset[str], int] = {}
    for t in transactions:
        present = sorted(t & frequent_items)
        for size in range(1, min(max_antecedent_size, len(present)) + 1):
            for combo in combinations(present, size):
                key = frozenset(combo)
                itemset_counts[key] = itemset_counts.get(key, 0) + 1
    itemset_counts = {k: v for k, v in itemset_counts.items() if v >= min_count}

    rules: list[dict[str, Any]] = []
    for itemset, count in itemset_counts.items():
        if len(itemset) < 2:
            continue
        for consequent in itemset:
            if not consequent.startswith(CONSEQUENT_PREFIXES):
                continue
            antecedent = itemset - {consequent}
            if not antecedent:
                continue
            ante_count = itemset_counts.get(antecedent)
            if not ante_count:
                continue
            cons_count = item_counts.get(consequent, 0)
            if cons_count == 0:
                continue

            support = count / n
            confidence = count / ante_count
            baseline = cons_count / n
            lift = confidence / baseline if baseline > 0 else 0.0

            if confidence < min_confidence or lift < min_lift:
                continue

            # Skip rules that are true by ontology construction rather than
            # by observation (e.g. energy_type -> lsr_tag).
            ante_fields = {i.partition("=")[0] for i in antecedent}
            cons_field = consequent.partition("=")[0]
            if any((af, cons_field) in TAUTOLOGICAL_PAIRS for af in ante_fields):
                continue

            ante_text = " + ".join(_phrase(i) for i in sorted(antecedent))
            cons_text = _phrase(consequent)
            rules.append({
                "antecedent": sorted(antecedent),
                "consequent": consequent,
                "antecedent_text": ante_text,
                "consequent_text": cons_text,
                "support": round(support, 4),
                "confidence": round(confidence, 4),
                "baseline": round(baseline, 4),
                "lift": round(lift, 3),
                "report_count": int(count),
                # Deliberately correlational wording. Never "causes".
                "statement": (
                    f"{ante_text} co-occurs with {cons_text} in "
                    f"{confidence:.0%} of cases, against a {baseline:.0%} baseline "
                    f"(lift {lift:.1f}, {count} reports)."
                ),
            })

    # Drop rules whose antecedent is a superset of a better-lift rule with the
    # same consequent — keeps the list readable instead of showing 8 variants
    # of the same finding.
    rules.sort(key=lambda r: (-r["lift"], -r["report_count"]))
    kept: list[dict[str, Any]] = []
    seen: list[tuple[frozenset[str], str]] = []
    for rule in rules:
        ante = frozenset(rule["antecedent"])
        cons = rule["consequent"]
        if any(prev_cons == cons and prev_ante <= ante for prev_ante, prev_cons in seen):
            continue
        seen.append((ante, cons))
        kept.append(rule)
        if len(kept) >= top_n:
            break

    return kept


def mine_barrier_failure_pairs(event_frames: Sequence[dict],
                               min_count: int = 5) -> list[dict[str, Any]]:
    """Focused view: (activity, barrier failure mode) pairs and their share of
    SIF-flagged reports. Powers the Barrier Failures screen."""
    pair_total: Counter = Counter()
    pair_sif: Counter = Counter()
    for f in event_frames:
        mode = f.get("barrier_failure_mode")
        activity = f.get("activity")
        if not mode or not activity:
            continue
        key = (str(activity), str(mode))
        pair_total[key] += 1
        if f.get("sif_potential"):
            pair_sif[key] += 1

    out = []
    for (activity, mode), total in pair_total.most_common():
        if total < min_count:
            continue
        sif = pair_sif.get((activity, mode), 0)
        out.append({
            "activity": activity,
            "barrier_failure_mode": mode,
            "report_count": total,
            "sif_count": sif,
            "sif_share": round(sif / total, 4),
        })
    out.sort(key=lambda r: (-r["sif_count"], -r["report_count"]))
    return out


__all__ = ["mine_associations", "mine_barrier_failure_pairs", "ITEM_FIELDS"]
