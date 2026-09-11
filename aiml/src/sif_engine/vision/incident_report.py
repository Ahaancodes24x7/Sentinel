"""Automatic complaint drafting for CCTV-detected incidents.

A camera that spots a fire and does nothing but colour a tile red has not
helped anybody. The requirement this module implements is that a detected
hazard is FILED - it becomes a real report, in the same queue, with the same
triage as one a person typed in, so it inherits every downstream capability
the platform already has: SIF classification, LSR tagging, review routing,
clustering, analytics and audit.

Two pieces are needed for that:

1. **A narrative a text pipeline can actually read.** The SIF engine consumes
   prose and extracts evidence spans from it. Feeding it a JSON blob or a
   terse event code would produce an empty extraction, so this module writes
   a proper field-report paragraph, using the vocabulary the shared ontology
   recognises for that hazard, and keeps the machine detail in a trailing
   evidence line where it does not distort span extraction.

2. **A priority that cannot silently under-call an emergency.** The text
   pipeline decides SIF potential from language. The camera separately knows
   how severe what it saw was. Priority is taken as the STRONGER of the two,
   never the average and never just the text verdict - see `derive_priority`.
   That is the direct implementation of the operating rule for this system:
   a false alarm is acceptable, an ignored report is not.

Everything written here is explicitly labelled as machine-generated and
unconfirmed. The narrative states what the camera observed and what that
might mean, and never asserts that a human verified it.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

# Priority ladder used across the console. P1 is "someone is dispatched now".
PRIORITY_P1 = "P1"
PRIORITY_P2 = "P2"
PRIORITY_P3 = "P3"
PRIORITY_P4 = "P4"

PRIORITY_LABELS: dict[str, str] = {
    PRIORITY_P1: "Immediate response",
    PRIORITY_P2: "Urgent review",
    PRIORITY_P3: "Elevated - review this shift",
    PRIORITY_P4: "Routine - log and monitor",
}

_PRIORITY_RANK = {PRIORITY_P4: 0, PRIORITY_P3: 1, PRIORITY_P2: 2, PRIORITY_P1: 3}

# Per-hazard framing for the generated narrative. `activity` is what the
# camera was watching, `lead` is the opening clause, and `hazard_terms` are
# the ontology-recognised words that must appear in the prose so Stage 1
# extraction has real spans to find rather than guessing.
_NARRATIVE: dict[str, dict[str, str]] = {
    "fire_detected": {
        "activity": "CCTV monitoring of an operating area",
        "lead": "CCTV analytics detected an open flame in the camera view",
        "hazard_terms": "fire, open flame and an active ignition source",
        "action": (
            "Emergency response required. Isolate ignition sources, confirm no "
            "hydrocarbon or dust inventory is exposed, and evacuate the immediate area."
        ),
    },
    "smoke_detected": {
        "activity": "CCTV monitoring of an operating area",
        "lead": "CCTV analytics detected a spreading smoke plume in the camera view",
        "hazard_terms": "smoke, possible fire and degraded escape routes",
        "action": (
            "Locate the source immediately, check for combustion, and confirm escape "
            "routes are still usable."
        ),
    },
    "visibility_loss": {
        "activity": "CCTV monitoring of an operating area",
        "lead": "CCTV analytics recorded a sharp loss of visibility across the camera view",
        "hazard_terms": "a suspected dust or gas cloud obscuring the working area",
        "action": (
            "Confirm atmospheric monitoring is live for this area, account for everyone "
            "working in it, and hold mobile plant movement until visibility recovers."
        ),
    },
    "person_fall": {
        "activity": "CCTV monitoring of personnel movement",
        "lead": "CCTV analytics detected a worker falling to the ground",
        "hazard_terms": "a fall, possible impact injury and possible fall from height",
        "action": (
            "Dispatch to the location and confirm the person is responsive and uninjured."
        ),
    },
    "person_down_immobile": {
        "activity": "CCTV monitoring of personnel movement",
        "lead": (
            "CCTV analytics detected a worker who went down and has remained motionless"
        ),
        "hazard_terms": (
            "an unresponsive casualty, possible oxygen deficient atmosphere and possible "
            "toxic exposure"
        ),
        "action": (
            "Man-down emergency. Dispatch rescue and medical response, and gas test before "
            "any rescuer enters the area."
        ),
    },
    "struck_by_falling_object": {
        "activity": "CCTV monitoring of an operating area",
        "lead": (
            "CCTV analytics detected a falling object reaching the immediate vicinity of a "
            "worker"
        ),
        "hazard_terms": "a falling object, dropped object and direct line of fire exposure",
        "action": (
            "Stop all work overhead, confirm the worker is unharmed, and inspect the source "
            "of the dropped object before restarting."
        ),
    },
    "falling_object": {
        "activity": "CCTV monitoring of an operating area",
        "lead": "CCTV analytics detected a mass falling rapidly through the camera view",
        "hazard_terms": "a falling object, possible roof fall and line of fire exposure",
        "action": (
            "Inspect ground support and overhead loads, and barricade the area until it is "
            "assessed."
        ),
    },
    "crowd_dispersal": {
        "activity": "CCTV monitoring of personnel movement",
        "lead": "CCTV analytics recorded several people leaving the area at once",
        "hazard_terms": "a possible unplanned evacuation from an unseen hazard",
        "action": (
            "Correlate with gas detection and adjacent cameras, and account for everyone "
            "assigned to the area."
        ),
    },
    "crowd_surge": {
        "activity": "CCTV monitoring of personnel movement",
        "lead": "CCTV analytics recorded several people entering the area at once",
        "hazard_terms": "unplanned crowding raising exposure in a working area",
        "action": "Confirm the gathering is planned and that the area is safe to occupy.",
    },
    "restricted_zone_entry": {
        "activity": "CCTV monitoring of a restricted zone",
        "lead": "CCTV analytics detected a person standing inside a configured restricted zone",
        "hazard_terms": "an unguarded hazard zone with live stored energy",
        "action": (
            "Verify the person is authorised, and that isolation and area controls for that "
            "zone are in place."
        ),
    },
    "lifting_zone_entry": {
        "activity": "CCTV monitoring of a lifting exclusion zone",
        "lead": (
            "CCTV analytics detected a person standing inside a configured lifting exclusion "
            "zone"
        ),
        "hazard_terms": "a suspended load overhead and line of fire exposure",
        "action": (
            "Stop the lift, clear the exclusion zone, and confirm the lift plan and "
            "barricading before resuming."
        ),
    },
    "vehicle_person_proximity": {
        "activity": "CCTV monitoring of a vehicle movement area",
        "lead": "CCTV analytics detected a person in close proximity to a moving vehicle",
        "hazard_terms": "vehicle-pedestrian interaction and line of fire exposure",
        "action": (
            "Confirm a banksman is controlling the movement and that pedestrian segregation "
            "is in place."
        ),
    },
}

_FALLBACK = {
    "activity": "CCTV monitoring of an operating area",
    "lead": "CCTV analytics detected a safety-relevant condition in the camera view",
    "hazard_terms": "an unclassified hazard requiring review",
    "action": "Review the footage and confirm the condition on site.",
}


def is_reportable(event_type: str) -> bool:
    """Whether this event type should raise an automatic complaint.

    Everything with a defined narrative is reportable. The default is
    deliberately permissive: an unrecognised event type still files under the
    fallback narrative rather than being dropped, because dropping is the one
    failure mode this system is not allowed to have.
    """
    return True


def derive_priority(
    vision_severity: str,
    sif_potential: bool,
    pipeline_confidence: float,
    vision_confidence: float,
) -> tuple[str, str]:
    """Combine the camera verdict and the text-pipeline verdict into one priority.

    Returns (priority, rationale).

    The rule is MAX, not average. The two assessments look at different
    evidence - the camera at pixels, the pipeline at language - and either one
    calling it serious is sufficient. Averaging them would let a confident
    text classifier talk a confirmed fire down to a routine log entry, which
    is exactly the failure this system exists to prevent.
    """
    severity = (vision_severity or "medium").lower()

    from_vision = {
        "critical": PRIORITY_P1,
        "high": PRIORITY_P2,
        "medium": PRIORITY_P3,
        "low": PRIORITY_P4,
    }.get(severity, PRIORITY_P3)

    # A high-severity sighting the camera is also confident about is not a
    # "review it later" item.
    if severity == "high" and vision_confidence >= 0.70:
        from_vision = PRIORITY_P1

    from_pipeline = PRIORITY_P4
    if sif_potential:
        from_pipeline = PRIORITY_P1 if pipeline_confidence >= 0.70 else PRIORITY_P2

    winner = max(from_vision, from_pipeline, key=lambda p: _PRIORITY_RANK[p])
    if _PRIORITY_RANK[from_vision] > _PRIORITY_RANK[from_pipeline]:
        rationale = (
            f"Priority set by the camera assessment ({severity} severity, "
            f"{vision_confidence:.0%} detection confidence); the text pipeline alone "
            f"would have routed this as {from_pipeline}."
        )
    elif _PRIORITY_RANK[from_pipeline] > _PRIORITY_RANK[from_vision]:
        rationale = (
            f"Priority set by the SIF text pipeline (SIF potential "
            f"{'yes' if sif_potential else 'no'}, {pipeline_confidence:.0%} confidence); "
            f"the camera assessment alone would have routed this as {from_vision}."
        )
    else:
        rationale = (
            f"Camera assessment ({severity} severity) and SIF text pipeline agree on "
            f"{winner}."
        )
    return winner, rationale


def build_narrative(event: dict[str, Any], site_name: Optional[str] = None) -> str:
    """Write the field-report prose for one vision event.

    Structure is fixed on purpose so the generated corpus stays consistent and
    the extraction stage sees the same shape every time:

        <where and when>. <what the camera saw>. <what it may mean>.
        <required action>. <machine evidence>. <provenance disclaimer>.
    """
    spec = _NARRATIVE.get(event.get("event_type", ""), _FALLBACK)
    camera_name = event.get("camera_name") or event.get("camera_id") or "an unnamed camera"
    where = site_name or event.get("site_id") or "the site"

    ts = event.get("timestamp")
    if isinstance(ts, datetime):
        when = ts.strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        when = str(ts) if ts else "an unrecorded time"

    observed = (event.get("observed") or "").strip().rstrip(".")
    inference = (event.get("inference") or "").strip().rstrip(".")
    evidence = (event.get("evidence") or "").strip().rstrip(".")
    roi = event.get("roi")
    zone_clause = f" inside the {roi} area" if roi else ""

    return (
        f"During {spec['activity']} at {where}, camera {camera_name} recorded the following "
        f"at {when}. {spec['lead']}{zone_clause}. Observed: {observed}. "
        f"The condition involves {spec['hazard_terms']}. "
        f"Assessment: {inference}. Required action: {spec['action']} "
        f"Detector evidence: {evidence}. "
        f"This report was generated automatically by the Sentinel CCTV analytics pipeline "
        f"and has not yet been confirmed by a person on site."
    )


def build_complaint(event: dict[str, Any], site_name: Optional[str] = None) -> dict[str, Any]:
    """Full auto-complaint payload for one vision event.

    The backend takes `report_text` through the normal SIF pipeline and then
    calls `derive_priority` with the result, so this module never has to
    import backend or pipeline code.
    """
    spec = _NARRATIVE.get(event.get("event_type", ""), _FALLBACK)
    return {
        "report_text": build_narrative(event, site_name=site_name),
        "activity": spec["activity"],
        "source_event_id": event.get("event_id"),
        "source_event_type": event.get("event_type"),
        "vision_severity": event.get("severity"),
        "vision_confidence": float(event.get("confidence") or 0.0),
        "camera_id": event.get("camera_id"),
        "camera_name": event.get("camera_name"),
        "recommended_action": spec["action"],
    }
