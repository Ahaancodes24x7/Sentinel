"""Intervention library tests.

Covers the evidence-matching behaviour added to `get_interventions`: each
curated intervention is tagged with the specific failure mode(s) it targets
(`addresses`), and matched against a pattern's own counted evidence
(`observed_failure_modes`) so the ranking - and the UI - can show which
control is backed by what this pattern's reports actually recorded, rather
than presenting the same flat list for every pattern under one barrier type.
"""

from sif_engine.recommendation.intervention_library import (
    INTERVENTIONS,
    get_interventions,
)
from sif_engine.recommendation.recommender import recommend


def test_every_curated_intervention_declares_what_it_addresses():
    """A control with no `addresses` at all can never be evidence-matched -
    catch a new entry added without one before it ships silent."""
    for barrier_type, items in INTERVENTIONS.items():
        for item in items:
            assert "addresses" in item, f"{barrier_type}: {item['action']!r} has no addresses list"
            assert isinstance(item["addresses"], list)


def test_hierarchy_of_controls_is_never_overridden_by_evidence_match():
    """The engineering control must rank first even when an administrative
    control further down the list has more matching evidence - evidence only
    breaks ties WITHIN a tier, it never promotes a weaker control past a
    stronger one. This is the one invariant that must never regress."""
    result = get_interventions(
        "Fall protection",
        observed_failure_modes={"harness not clipped": 40},  # matches only admin/training items
    )
    assert result[0]["control_level"] == "engineering"
    assert result[0]["evidence_match_count"] == 0


def test_evidence_match_reorders_within_a_tier():
    result = get_interventions(
        "Energy isolation & LOTO",
        observed_failure_modes={"lock or tag missing": 20, "isolation not verified": 2},
    )
    admin_items = [r for r in result if r["control_level"] == "administrative"]
    assert len(admin_items) == 2
    # "Supervisor sign-off..." addresses "lock or tag missing" (20 reports);
    # "Mandatory independent isolation verification..." addresses
    # "isolation not verified" (2 reports) - the higher-evidence one must sort first.
    assert admin_items[0]["evidence_match_count"] == 20
    assert admin_items[1]["evidence_match_count"] == 2


def test_unrelated_observed_failure_modes_are_not_matched():
    """A count for a failure mode this barrier type has nothing to do with
    must not silently attach itself to an unrelated intervention."""
    result = get_interventions(
        "Machine guarding",
        observed_failure_modes={"speed limit exceeded": 99},  # belongs to Traffic & journey management
    )
    assert all(r["evidence_match_count"] == 0 for r in result)
    assert all(r["matched_failure_modes"] == [] for r in result)


def test_no_observed_modes_still_returns_full_ranked_list():
    """recommend() must work identically to before observed_failure_modes
    existed when a pattern has no barrier_failure_mode on any member frame."""
    result = get_interventions("Permit to work")
    assert len(result) == 4
    assert all(r["evidence_match_count"] == 0 for r in result)
    assert [r["rank"] for r in result] == [1, 2, 3, 4]


def test_recommend_passes_this_patterns_own_evidence_through():
    """End-to-end: recommend() must compute observed_failure_modes from the
    SAME member_frames it reports evidence counts from, not a separate or
    stale source - otherwise the UI's evidence-match claim could point at
    reports the intervention list was not actually built from."""
    member_frames = [
        {"report_id": "r1", "barrier_type": "Energy isolation & LOTO",
         "barrier_failure_mode": "isolation not verified", "activity": "electrical panel work"},
        {"report_id": "r2", "barrier_type": "Energy isolation & LOTO",
         "barrier_failure_mode": "isolation not verified", "activity": "electrical panel work"},
        {"report_id": "r3", "barrier_type": "Energy isolation & LOTO",
         "barrier_failure_mode": "lock or tag missing", "activity": "electrical panel work"},
    ]
    pattern = {"cluster_id": "c1", "member_report_ids": ["r1", "r2", "r3"]}
    result = recommend(pattern, member_frames)

    matched = {
        iv["action"]: iv["evidence_match_count"]
        for iv in result["recommended_interventions"]
        if iv["evidence_match_count"] > 0
    }
    assert any(count == 2 for count in matched.values())  # "isolation not verified" x2
    assert any(count == 1 for count in matched.values())  # "lock or tag missing" x1
    # And the evidence breakdown that justifies it is the same evidence trail
    # shown elsewhere on the pattern, not a second, disconnected computation.
    assert result["evidence"]["breakdown"]["failure_mode::isolation not verified"] == 2
