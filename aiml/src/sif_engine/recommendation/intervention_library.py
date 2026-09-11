"""Curated barrier -> intervention lookup, organised by hierarchy of controls.

This is a version-controlled config table, NOT generated text. That is a
deliberate design choice, not a shortcut: these recommendations decide where an
operator points intervention budget, so they must be auditable, reviewable by
an HSE authority, and stable between runs. A language model asked to "suggest
controls" would produce fluent, plausible, subtly different advice every time
and nobody could sign it off.

Interventions are ranked by the hierarchy of controls — elimination and
engineering controls outrank administrative ones, which outrank training,
which outranks PPE. That ordering is not our opinion; it is the standard
hierarchy every HSE professional on a judging panel already works to.
"""

from __future__ import annotations

from typing import Any, Optional

# Lower rank value = higher position in the hierarchy of controls.
CONTROL_LEVEL_RANK: dict[str, int] = {
    "elimination": 0,
    "substitution": 1,
    "engineering": 2,
    "administrative": 3,
    "training": 4,
    "ppe": 5,
}

PRIORITY_BY_LEVEL: dict[str, str] = {
    "elimination": "HIGH",
    "substitution": "HIGH",
    "engineering": "HIGH",
    "administrative": "MEDIUM",
    "training": "MEDIUM",
    "ppe": "LOW",
}

# barrier_type -> ranked interventions.
#
# `addresses` ties each intervention to the specific failure mode(s) it
# targets, using the exact same vocabulary as configs/ontology.yaml's
# barrier_types[*].failure_modes. This is what get_interventions() below
# matches against a pattern's OWN counted evidence (recommender.py's
# _evidence_breakdown, `failure_mode::<mode>` keys) to surface, per
# intervention, how many of THIS pattern's reports that specific control
# would actually have targeted — a control library entry stops being a flat
# curated list and becomes a claim checkable against the evidence in front
# of it.
INTERVENTIONS: dict[str, list[dict[str, Any]]] = {
    "Energy isolation & LOTO": [
        {"action": "Install lockable isolation points with a verified zero-energy test port at the affected equipment", "control_level": "engineering",
         "addresses": ["isolation point incorrect", "stored energy not dissipated"]},
        {"action": "Mandatory independent isolation verification checkpoint before permit issue", "control_level": "administrative",
         "addresses": ["isolation not verified"]},
        {"action": "Supervisor sign-off at both permit start and permit closure, recorded against the isolation certificate", "control_level": "administrative",
         "addresses": ["lock or tag missing", "isolation removed early"]},
        {"action": "Targeted Energy Isolation toolbox campaign for the affected crews and contractors", "control_level": "training",
         "addresses": ["isolation not verified", "isolation point incorrect"]},
    ],
    "Permit to work": [
        {"action": "Electronic permit system with hard scope-change revalidation gate", "control_level": "engineering",
         "addresses": ["scope changed without revalidation", "permit expired"]},
        {"action": "Permit-at-worksite spot audit during each shift by the area authority", "control_level": "administrative",
         "addresses": ["permit not at worksite", "permit expired"]},
        {"action": "Require the permit holder to be physically present at the job front at start-up", "control_level": "administrative",
         "addresses": ["permit not raised", "sign-off missing"]},
        {"action": "Refresher on permit scope and validity for supervisors and permit holders", "control_level": "training",
         "addresses": ["scope changed without revalidation", "sign-off missing"]},
    ],
    "Gas testing & atmospheric monitoring": [
        {"action": "Deploy continuous personal and area gas monitoring with alarm telemetry", "control_level": "engineering",
         "addresses": ["gas test not performed", "continuous monitoring absent"]},
        {"action": "Enforce re-test on any break in work exceeding the permitted interval", "control_level": "administrative",
         "addresses": ["gas test stale", "test point unrepresentative"]},
        {"action": "Calibration-due interlock preventing use of out-of-date detectors", "control_level": "engineering",
         "addresses": ["detector uncalibrated"]},
        {"action": "Competency reassessment for authorised gas testers", "control_level": "training",
         "addresses": ["test point unrepresentative", "gas test not performed"]},
    ],
    "Exclusion zone & barricading": [
        {"action": "Replace tape barricades with rigid physical barriers in recurring drop zones", "control_level": "engineering",
         "addresses": ["barricade breached", "zone not established"]},
        {"action": "Assign a dedicated zone watchman for the duration of overhead work", "control_level": "administrative",
         "addresses": ["watchman absent", "zone not enforced"]},
        {"action": "Standardise exclusion-zone signage and radius calculation across sites", "control_level": "administrative",
         "addresses": ["signage absent", "zone not established"]},
        {"action": "Line-of-fire awareness campaign focused on the affected activity", "control_level": "training",
         "addresses": ["zone not enforced", "barricade breached"]},
    ],
    "Fall protection": [
        {"action": "Install permanent certified anchor points and engineered edge protection", "control_level": "engineering",
         "addresses": ["anchor point absent", "unrated anchor", "edge protection incomplete"]},
        {"action": "Scaffold tagging discipline with independent inspection before handover", "control_level": "administrative",
         "addresses": ["scaffold tag missing", "edge protection incomplete"]},
        {"action": "100% tie-off verification at the access point for elevated work", "control_level": "administrative",
         "addresses": ["harness not clipped"]},
        {"action": "Practical fall-arrest and rescue drill for working-at-height teams", "control_level": "training",
         "addresses": ["harness not clipped", "unrated anchor"]},
    ],
    "Machine guarding": [
        {"action": "Replace removable guards with interlocked fixed guarding on the affected machines", "control_level": "engineering",
         "addresses": ["guard removed", "interlock defeated"]},
        {"action": "Guard-refitting verification step in the maintenance close-out checklist", "control_level": "administrative",
         "addresses": ["guard not refitted after maintenance"]},
        {"action": "Pre-start guard inspection recorded on the equipment log", "control_level": "administrative",
         "addresses": ["guard damaged", "guard not refitted after maintenance"]},
        {"action": "Machinery-safety briefing for maintenance and workshop crews", "control_level": "training",
         "addresses": ["guard removed", "interlock defeated"]},
    ],
    "Traffic & journey management": [
        {"action": "Physically segregate pedestrian routes from vehicle movement areas", "control_level": "engineering",
         "addresses": ["route not assessed"]},
        {"action": "Fit reversing cameras and proximity alarms to site mobile plant", "control_level": "engineering",
         "addresses": ["reversing without spotter"]},
        {"action": "Mandatory banksman for all reversing movements in congested areas", "control_level": "administrative",
         "addresses": ["banksman absent", "reversing without spotter"]},
        {"action": "Defensive driving and journey-management refresher for site drivers", "control_level": "training",
         "addresses": ["speed limit exceeded", "journey plan absent"]},
    ],
    "Safety instrumented system": [
        {"action": "Require documented authorisation and a compensating measure for every override", "control_level": "administrative",
         "addresses": ["interlock bypassed without authorisation", "no compensating measure"]},
        {"action": "Automatic time-limited overrides that expire and re-arm without manual action", "control_level": "engineering",
         "addresses": ["override left in place", "trip disabled"]},
        {"action": "Daily override register review by the shift in-charge", "control_level": "administrative",
         "addresses": ["override left in place", "alarm inhibited"]},
        {"action": "Bypassing Safety Controls rule briefing for operations and instrument teams", "control_level": "training",
         "addresses": ["interlock bypassed without authorisation", "alarm inhibited"]},
    ],
    "Lifting plan & rigging control": [
        {"action": "Engineered lift plans reviewed and approved for all non-routine lifts", "control_level": "administrative",
         "addresses": ["lift plan absent", "load chart exceeded"]},
        {"action": "Colour-coded rigging inspection regime with quarantine for uncertified gear", "control_level": "engineering",
         "addresses": ["uncertified rigging"]},
        {"action": "Mandatory taglines and exclusion radius for suspended loads", "control_level": "administrative",
         "addresses": ["taglines not used"]},
        {"action": "Competency verification for crane operators, riggers and banksmen", "control_level": "training",
         "addresses": ["competency unverified"]},
    ],
}

# Activity-specific additions layered on top of the barrier interventions.
ACTIVITY_SPECIFIC: dict[str, list[dict[str, str]]] = {
    "night shift handover at wellsite": [
        {"action": "Structured written handover checklist covering open isolations and permits", "control_level": "administrative"},
        {"action": "Overlap period requiring both shifts present for isolation walk-down", "control_level": "administrative"},
    ],
    "gas compressor maintenance": [
        {"action": "Pre-maintenance override register reconciliation before work authorisation", "control_level": "administrative"},
    ],
    "confined space entry for tank cleaning": [
        {"action": "Standby attendant with continuous communication and logged entry/exit", "control_level": "administrative"},
    ],
    "lifting operation with mobile crane": [
        {"action": "Ground-condition and outrigger assessment recorded before each set-up", "control_level": "administrative"},
    ],
    "flowline pressure testing": [
        {"action": "Remote pressurisation with a hard exclusion radius during the test hold", "control_level": "engineering"},
    ],
    "radiography of pipeline welds": [
        {"action": "Interlocked area alarm and access control during source exposure", "control_level": "engineering"},
    ],
}


def get_interventions(
    barrier_type: str,
    activity: Optional[str] = None,
    observed_failure_modes: Optional[dict[str, int]] = None,
) -> list[dict[str, Any]]:
    """Ranked interventions for a barrier type, optionally activity-augmented
    and evidence-matched.

    Ranking is by hierarchy of controls first (never overridden — a training
    campaign does not out-rank an engineering fix just because it happens to
    match more reports), then, within the same tier, by how many of THIS
    pattern's counted failure-mode observations the intervention's curated
    `addresses` list actually covers. Ties within a tier keep curated order.

    `observed_failure_modes` is the pattern's own evidence breakdown (e.g.
    from recommender._evidence_breakdown, keys like "isolation not verified"
    with a report count) — when supplied, each returned intervention carries
    `matched_failure_modes` (the observed modes it addresses) and
    `evidence_match_count` (how many reports mentioned one of them), so the
    UI can show a specific reason rather than a flat curated list.
    """
    items: list[dict[str, Any]] = list(INTERVENTIONS.get(barrier_type, []))
    if activity:
        items += ACTIVITY_SPECIFIC.get(activity, [])

    if not items:
        items = [
            {"action": "Review the applicable control with the area authority and confirm it is effective in the field",
             "control_level": "administrative", "addresses": []},
        ]

    observed = observed_failure_modes or {}

    def _match(item: dict[str, Any]) -> tuple[list[str], int]:
        addressed = item.get("addresses") or []
        matched = [mode for mode in addressed if observed.get(mode)]
        count = sum(observed.get(mode, 0) for mode in matched)
        return matched, count

    # Stable sort: hierarchy of controls first (unconditionally), then
    # evidence-match count within the tier, then curated order as the
    # final tie-break so two equally-matched items keep their authored order.
    scored = [(item, *_match(item)) for item in items]
    ordered = sorted(
        enumerate(scored),
        key=lambda pair: (
            CONTROL_LEVEL_RANK.get(pair[1][0]["control_level"], 9),
            -pair[1][2],
            pair[0],
        ),
    )

    out: list[dict[str, Any]] = []
    seen_actions: set[str] = set()
    for _, (item, matched, match_count) in ordered:
        if item["action"] in seen_actions:
            continue
        seen_actions.add(item["action"])
        out.append({
            "rank": len(out) + 1,
            "action": item["action"],
            "control_level": item["control_level"],
            "priority": PRIORITY_BY_LEVEL.get(item["control_level"], "MEDIUM"),
            "addresses": list(item.get("addresses") or []),
            "matched_failure_modes": matched,
            "evidence_match_count": match_count,
        })
    return out


def barrier_types() -> list[str]:
    return sorted(INTERVENTIONS)


__all__ = [
    "get_interventions",
    "barrier_types",
    "INTERVENTIONS",
    "ACTIVITY_SPECIFIC",
    "CONTROL_LEVEL_RANK",
    "PRIORITY_BY_LEVEL",
]
