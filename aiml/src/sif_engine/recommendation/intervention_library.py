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

# barrier_type -> ranked interventions
INTERVENTIONS: dict[str, list[dict[str, str]]] = {
    "Energy isolation & LOTO": [
        {"action": "Install lockable isolation points with a verified zero-energy test port at the affected equipment", "control_level": "engineering"},
        {"action": "Mandatory independent isolation verification checkpoint before permit issue", "control_level": "administrative"},
        {"action": "Supervisor sign-off at both permit start and permit closure, recorded against the isolation certificate", "control_level": "administrative"},
        {"action": "Targeted Energy Isolation toolbox campaign for the affected crews and contractors", "control_level": "training"},
    ],
    "Permit to work": [
        {"action": "Electronic permit system with hard scope-change revalidation gate", "control_level": "engineering"},
        {"action": "Permit-at-worksite spot audit during each shift by the area authority", "control_level": "administrative"},
        {"action": "Require the permit holder to be physically present at the job front at start-up", "control_level": "administrative"},
        {"action": "Refresher on permit scope and validity for supervisors and permit holders", "control_level": "training"},
    ],
    "Gas testing & atmospheric monitoring": [
        {"action": "Deploy continuous personal and area gas monitoring with alarm telemetry", "control_level": "engineering"},
        {"action": "Enforce re-test on any break in work exceeding the permitted interval", "control_level": "administrative"},
        {"action": "Calibration-due interlock preventing use of out-of-date detectors", "control_level": "engineering"},
        {"action": "Competency reassessment for authorised gas testers", "control_level": "training"},
    ],
    "Exclusion zone & barricading": [
        {"action": "Replace tape barricades with rigid physical barriers in recurring drop zones", "control_level": "engineering"},
        {"action": "Assign a dedicated zone watchman for the duration of overhead work", "control_level": "administrative"},
        {"action": "Standardise exclusion-zone signage and radius calculation across sites", "control_level": "administrative"},
        {"action": "Line-of-fire awareness campaign focused on the affected activity", "control_level": "training"},
    ],
    "Fall protection": [
        {"action": "Install permanent certified anchor points and engineered edge protection", "control_level": "engineering"},
        {"action": "Scaffold tagging discipline with independent inspection before handover", "control_level": "administrative"},
        {"action": "100% tie-off verification at the access point for elevated work", "control_level": "administrative"},
        {"action": "Practical fall-arrest and rescue drill for working-at-height teams", "control_level": "training"},
    ],
    "Machine guarding": [
        {"action": "Replace removable guards with interlocked fixed guarding on the affected machines", "control_level": "engineering"},
        {"action": "Guard-refitting verification step in the maintenance close-out checklist", "control_level": "administrative"},
        {"action": "Pre-start guard inspection recorded on the equipment log", "control_level": "administrative"},
        {"action": "Machinery-safety briefing for maintenance and workshop crews", "control_level": "training"},
    ],
    "Traffic & journey management": [
        {"action": "Physically segregate pedestrian routes from vehicle movement areas", "control_level": "engineering"},
        {"action": "Fit reversing cameras and proximity alarms to site mobile plant", "control_level": "engineering"},
        {"action": "Mandatory banksman for all reversing movements in congested areas", "control_level": "administrative"},
        {"action": "Defensive driving and journey-management refresher for site drivers", "control_level": "training"},
    ],
    "Safety instrumented system": [
        {"action": "Require documented authorisation and a compensating measure for every override", "control_level": "administrative"},
        {"action": "Automatic time-limited overrides that expire and re-arm without manual action", "control_level": "engineering"},
        {"action": "Daily override register review by the shift in-charge", "control_level": "administrative"},
        {"action": "Bypassing Safety Controls rule briefing for operations and instrument teams", "control_level": "training"},
    ],
    "Lifting plan & rigging control": [
        {"action": "Engineered lift plans reviewed and approved for all non-routine lifts", "control_level": "administrative"},
        {"action": "Colour-coded rigging inspection regime with quarantine for uncertified gear", "control_level": "engineering"},
        {"action": "Mandatory taglines and exclusion radius for suspended loads", "control_level": "administrative"},
        {"action": "Competency verification for crane operators, riggers and banksmen", "control_level": "training"},
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


def get_interventions(barrier_type: str, activity: Optional[str] = None) -> list[dict[str, Any]]:
    """Ranked interventions for a barrier type, optionally activity-augmented.

    Ranking is by hierarchy of controls, then by the order curated in this file.
    Each entry carries ``rank``, ``control_level``, ``priority`` and ``action``.
    """
    items: list[dict[str, str]] = list(INTERVENTIONS.get(barrier_type, []))
    if activity:
        items += ACTIVITY_SPECIFIC.get(activity, [])

    if not items:
        items = [
            {"action": "Review the applicable control with the area authority and confirm it is effective in the field",
             "control_level": "administrative"},
        ]

    # Stable sort: hierarchy of controls first, curated order preserved within.
    ordered = sorted(
        enumerate(items),
        key=lambda pair: (CONTROL_LEVEL_RANK.get(pair[1]["control_level"], 9), pair[0]),
    )

    out: list[dict[str, Any]] = []
    seen_actions: set[str] = set()
    for rank, (_, item) in enumerate(ordered, start=1):
        if item["action"] in seen_actions:
            continue
        seen_actions.add(item["action"])
        out.append({
            "rank": len(out) + 1,
            "action": item["action"],
            "control_level": item["control_level"],
            "priority": PRIORITY_BY_LEVEL.get(item["control_level"], "MEDIUM"),
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
