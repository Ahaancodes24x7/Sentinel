"""Safety-event rule layer for mine / field CCTV hazard monitoring.

Two very different inputs arrive here and are turned into one uniform event
stream:

  1. `detections`  - COCO-class boxes from YOLO. Answers "who and what is in
                     the frame": people, vehicles, plant.
  2. `signals`     - SceneSignals from scene_analysis.py. Answers "what is the
                     scene doing": burning, filling with smoke, losing
                     visibility, dropping a mass onto someone, a worker going
                     from upright to prone and staying there.

The taxonomy below is ordered by how a control room would triage it, and it
is deliberately weighted toward the disaster precursors that matter
underground and on a field site - fire, smoke, obscuration, roof/rock fall,
struck-by, a worker down - rather than only the zone-access rules a
detection-only system can express.

Two invariants every rule keeps:

* OBSERVATION and INFERENCE stay separate. `observed` states only what the
  pixels did. `inference` is the safety reading a human still confirms. No
  rule writes a conclusion into `observed`.
* RECALL BEATS PRECISION. The system is explicitly specified to tolerate
  false alarms and to tolerate no misses, so weak evidence still raises an
  event - carrying a low confidence and, where relevant, an explicit
  "possible" hedge in the inference text, so the operator sees the strength
  of the call instead of a flat alarm.

PPE (helmet/vest) detection is still NOT claimed. The pretrained detector
cannot see PPE, and inventing a "helmet missing" event from a model with no
helmet class would be a dishonest claim. A dedicated PPE model can be added
later as another rule reading its own detector output; `evaluate()` already
takes plain lists, so that needs no restructuring here.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from typing import Optional

from .detector import DetectedObject
from .incident_report import is_reportable
from .scene_analysis import SceneSignals

VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle", "train", "boat", "airplane"}

# Normalized distance between bbox centers below which a person and a vehicle
# count as being in close proximity. Frame-diagonal-relative, so it behaves
# the same at any capture resolution.
PROXIMITY_THRESHOLD = 0.18

# Per-event-type debounce. Without this a fire burning for a minute at 2 fps
# would raise ~120 duplicate events instead of one that stays active until
# a controller acknowledges it. Tuned per type: a fire that is still burning
# 20 s later is worth restating, a zone entry is not.
EVENT_COOLDOWN_SECONDS = 12.0
COOLDOWNS: dict[str, float] = {
    "fire_detected": 20.0,
    "smoke_detected": 25.0,
    "visibility_loss": 30.0,
    "person_fall": 12.0,
    "person_down_immobile": 25.0,
    "struck_by_falling_object": 10.0,
    "falling_object": 12.0,
    "crowd_dispersal": 20.0,
    "crowd_surge": 20.0,
    "restricted_zone_entry": 15.0,
    "lifting_zone_entry": 15.0,
    "vehicle_person_proximity": 12.0,
}

SEVERITY_ORDER = {"critical": 3, "high": 2, "medium": 1, "low": 0}


@dataclass
class EventDraft:
    event_type: str
    severity: str
    confidence: float
    objects: list[DetectedObject]
    evidence: str
    roi: Optional[str]
    observed: str
    inference: str
    sif_relevance: str
    lsr_tag: str
    dedupe_key: str
    hazard_class: str = "scene"
    regions: list[dict] = field(default_factory=list)

    @property
    def auto_report(self) -> bool:
        """Whether this event raises an automatic complaint.

        Delegated to incident_report so the reporting policy lives in exactly
        one place. Keeping a second list here would be a policy that silently
        drifts out of step with the one the backend actually consults - and the
        direction it would drift is toward hazards quietly not being reported,
        which is the one failure this system may not have.
        """
        return is_reportable(self.event_type)

    def cooldown(self) -> float:
        return COOLDOWNS.get(self.event_type, EVENT_COOLDOWN_SECONDS)


def _point_in_polygon(x: float, y: float, polygon: list[list[float]]) -> bool:
    """Ray-casting point-in-polygon test over normalized coordinates."""
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_at_y = x1 + (y - y1) * (x2 - x1) / (y2 - y1 + 1e-12)
            if x < x_at_y:
                inside = not inside
    return inside


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _feet(det: DetectedObject) -> tuple[float, float]:
    """Ground contact point of a person box: bottom edge, horizontal centre.

    Zone membership has to be tested where the person is STANDING, not at the
    centre of their bounding box. Using the centre makes a distant person
    whose head happens to overlap a zone drawn on the far wall register as
    being inside it, which is the single largest source of false zone alarms
    in a naive implementation.
    """
    x1, _y1, x2, y2 = det.bbox
    return (x1 + x2) / 2.0, y2


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def _article(label: str, descending: bool = False) -> str:
    """Sentence-initial noun phrase with the right indefinite article.

    Object labels come from the detector class list and from the motion-blob
    fallback, so the leading vowel is not known in advance and a hardcoded "A"
    produces "A unidentified mass" in operator-facing text.
    """
    word = f"descending {label}" if descending else label
    article = "An" if word[:1].lower() in "aeiou" else "A"
    return f"{article} {word}"


# ---------------------------------------------------------------------------
# Scene-level rules (fire, smoke, obscuration, falls, dropped masses)
# ---------------------------------------------------------------------------
def _scene_rules(signals: SceneSignals, camera: dict, persons: list[DetectedObject]) -> list[EventDraft]:
    camera_id = camera.get("camera_id", "")
    drafts: list[EventDraft] = []
    people_here = len(persons)
    exposure = (
        f" {people_here} person(s) were in frame at the time."
        if people_here
        else " No person was detected in frame at the time."
    )

    # ---- FIRE ------------------------------------------------------------
    if signals.fire_active:
        area = sum(r.area_ratio for r in signals.fire_regions)
        severity = "critical" if (people_here or signals.smoke_active or area >= 0.01) else "high"
        drafts.append(EventDraft(
            event_type="fire_detected",
            severity=severity,
            confidence=round(max(signals.fire_score, 0.45), 3),
            objects=persons[:4],
            evidence=(
                f"flame-colour mask over {_pct(area)} of frame across "
                f"{len(signals.fire_regions)} region(s), with frame-to-frame flicker "
                f"consistent with combustion (fire index {signals.fire_score:.2f})"
            ),
            roi=None,
            observed=(
                "A flickering flame-coloured source was detected in the camera view." + exposure
            ),
            inference=(
                "Probable open flame / active fire. Treat as an ignition event until "
                "visually confirmed: isolate ignition sources, evacuate the immediate area "
                "and verify no hydrocarbon or dust inventory is exposed."
            ),
            sif_relevance=(
                "Fatality-potential event. Fire in an operating area is a direct SIF "
                "precursor and an immediate emergency-response trigger."
            ),
            lsr_tag="Hot Work",
            dedupe_key=f"{camera_id}:fire_detected",
            hazard_class="fire",
            regions=[r.to_dict() for r in signals.fire_regions],
        ))

    # ---- SMOKE -----------------------------------------------------------
    if signals.smoke_active:
        area = sum(r.area_ratio for r in signals.smoke_regions)
        severity = "critical" if signals.fire_active else "high"
        drafts.append(EventDraft(
            event_type="smoke_detected",
            severity=severity,
            confidence=round(max(signals.smoke_score, 0.40), 3),
            objects=persons[:4],
            evidence=(
                f"desaturated moving region covering {_pct(area)} of frame with edge energy "
                f"below the scene average (smoke index {signals.smoke_score:.2f}, "
                f"visibility {signals.visibility:.2f})"
            ),
            roi=None,
            observed=(
                "A grey, moving, low-texture plume was detected spreading across the "
                "camera view." + exposure
            ),
            inference=(
                "Possible smoke from combustion, or a released dust/vapour cloud. Locate "
                "the source before it obscures escape routes; if combustion is confirmed "
                "this is a developing fire."
            ),
            sif_relevance=(
                "Smoke in an enclosed or underground workplace carries both asphyxiation "
                "and fire-escalation potential, and degrades every escape route at once."
            ),
            lsr_tag="Hot Work",
            dedupe_key=f"{camera_id}:smoke_detected",
            hazard_class="smoke",
            regions=[r.to_dict() for r in signals.smoke_regions],
        ))

    # ---- VISIBILITY LOSS -------------------------------------------------
    if signals.visibility_active and not signals.smoke_active:
        drafts.append(EventDraft(
            event_type="visibility_loss",
            severity="high" if people_here else "medium",
            confidence=round(0.40 + 0.45 * signals.visibility_drop, 3),
            objects=persons[:4],
            evidence=(
                f"scene edge energy fell {_pct(signals.visibility_drop)} below the rolling "
                f"baseline for this camera (visibility index {signals.visibility:.2f})"
            ),
            roi=None,
            observed=(
                "Scene detail dropped sharply against the baseline for this camera - the "
                "view is being obscured." + exposure
            ),
            inference=(
                "Possible dust cloud, gas release, water ingress or smoke layer reducing "
                "visibility. Workers in this area may lose sight of escape routes and of "
                "moving plant."
            ),
            sif_relevance=(
                "Sudden loss of visibility precedes struck-by, entrapment and "
                "failed-evacuation outcomes, and can indicate an uncontrolled release."
            ),
            lsr_tag="Confined Space",
            dedupe_key=f"{camera_id}:visibility_loss",
            hazard_class="atmosphere",
        ))

    # ---- PERSON FALL / COLLAPSE ------------------------------------------
    for fall in signals.falls:
        box_region = [{
            "kind": "casualty",
            "bbox": [round(v, 4) for v in fall.bbox],
            "score": round(fall.confidence, 3),
            "area_ratio": 0.0,
        }]
        if fall.kind == "fall":
            drafts.append(EventDraft(
                event_type="person_fall",
                severity="high",
                confidence=round(fall.confidence, 3),
                objects=persons[:2],
                evidence=(
                    f"tracked person #{fall.track_id} posture ratio {fall.aspect_before} to "
                    f"{fall.aspect_after} with downward centroid speed {fall.drop_speed} "
                    f"frame-heights/s"
                ),
                roi=None,
                observed=(
                    "A tracked person went from an upright to a horizontal posture within "
                    "about a second, with rapid downward movement."
                ),
                inference=(
                    "Probable fall or collapse. Could be a slip or trip, a fall from height, "
                    "a struck-by, or a medical or atmospheric collapse - dispatch and confirm "
                    "the person is responsive."
                ),
                sif_relevance=(
                    "Falls are among the highest-frequency fatality mechanisms in mining and "
                    "field operations, and response time drives the outcome."
                ),
                lsr_tag="Working at Height",
                dedupe_key=f"{camera_id}:person_fall:{fall.track_id}",
                hazard_class="person_down",
                regions=box_region,
            ))
        else:
            drafts.append(EventDraft(
                event_type="person_down_immobile",
                severity="critical",
                confidence=round(fall.confidence, 3),
                objects=persons[:2],
                evidence=(
                    f"tracked person #{fall.track_id} remained prone and motionless for "
                    f"{fall.still_seconds}s after going down"
                ),
                roi=None,
                observed=(
                    f"A person who went down has not moved for {fall.still_seconds} seconds "
                    "and remains in a horizontal posture."
                ),
                inference=(
                    "Probable unresponsive casualty. Treat as a man-down emergency: dispatch "
                    "rescue and medical response, and check the atmosphere before anyone "
                    "enters to help."
                ),
                sif_relevance=(
                    "An immobile worker is either injured or unconscious. In an "
                    "atmosphere-related collapse the rescuer becomes the next casualty, which "
                    "is how single incidents become multiple fatalities."
                ),
                lsr_tag="Working at Height",
                dedupe_key=f"{camera_id}:person_down_immobile:{fall.track_id}",
                hazard_class="person_down",
                regions=box_region,
            ))

    # ---- FALLING OBJECT / ROOF FALL --------------------------------------
    for obj in signals.falling_objects:
        obj_region = [{
            "kind": "falling",
            "bbox": [round(v, 4) for v in obj.bbox],
            "score": round(obj.confidence, 3),
            "area_ratio": obj.area_ratio,
        }]
        if obj.near_person:
            drafts.append(EventDraft(
                event_type="struck_by_falling_object",
                severity="critical",
                confidence=round(obj.confidence, 3),
                objects=persons[:2],
                evidence=(
                    f"{obj.label} descending at {obj.descent_speed} frame-heights/s closed to "
                    f"within {obj.gap} of a detected person"
                ),
                roi=None,
                observed=(
                    f"{_article(obj.label, descending=True)} reached the immediate vicinity of "
                    "a person in the camera view."
                ),
                inference=(
                    "Probable struck-by or dropped-object impact on a worker. Treat as a "
                    "casualty event until the person is confirmed unharmed, and stop all work "
                    "overhead."
                ),
                sif_relevance=(
                    "Dropped objects and roof or rock falls onto workers are a leading cause "
                    "of fatalities underground. Any near-contact is a direct SIF precursor."
                ),
                lsr_tag="Line of Fire",
                dedupe_key=f"{camera_id}:struck_by_falling_object",
                hazard_class="impact",
                regions=obj_region,
            ))
        else:
            drafts.append(EventDraft(
                event_type="falling_object",
                severity="high",
                confidence=round(obj.confidence, 3),
                objects=persons[:2],
                evidence=(
                    f"{obj.label} covering {_pct(obj.area_ratio)} of frame descending at "
                    f"{obj.descent_speed} frame-heights/s with no matching lateral motion"
                ),
                roi=None,
                observed=(
                    f"{_article(obj.label)} moved rapidly down the frame under what appears "
                    "to be gravity." + exposure
                ),
                inference=(
                    "Possible dropped object, roof fall or rock fall. Inspect ground support "
                    "and overhead loads before anyone re-enters the area."
                ),
                sif_relevance=(
                    "Ground or roof instability and dropped objects escalate quickly; the "
                    "first fall is usually the warning before a larger collapse."
                ),
                lsr_tag="Line of Fire",
                dedupe_key=f"{camera_id}:falling_object",
                hazard_class="impact",
                regions=obj_region,
            ))

    # ---- CROWD BEHAVIOUR --------------------------------------------------
    if signals.crowd_event == "dispersal":
        drafts.append(EventDraft(
            event_type="crowd_dispersal",
            severity="high",
            confidence=0.55,
            objects=persons[:6],
            evidence=(
                f"person count changed by {signals.occupancy_delta} between consecutive "
                f"analysed frames (now {signals.person_count})"
            ),
            roi=None,
            observed="Several people left the camera view at once.",
            inference=(
                "Possible self-evacuation from a hazard the camera cannot see directly. "
                "Correlate with gas detection and with the adjacent cameras."
            ),
            sif_relevance=(
                "A sudden unplanned evacuation is often the earliest human signal of a "
                "release, an ignition or a ground-movement event."
            ),
            lsr_tag="Work Authorisation",
            dedupe_key=f"{camera_id}:crowd_dispersal",
            hazard_class="behaviour",
        ))
    elif signals.crowd_event == "surge":
        drafts.append(EventDraft(
            event_type="crowd_surge",
            severity="medium",
            confidence=0.45,
            objects=persons[:6],
            evidence=(
                f"person count rose by {signals.occupancy_delta} between consecutive "
                f"analysed frames (now {signals.person_count})"
            ),
            roi=None,
            observed="Several people entered the camera view at once.",
            inference=(
                "Possible unplanned gathering, or a group responding to an incident just "
                "outside this camera view."
            ),
            sif_relevance=(
                "Unplanned crowding raises exposure if the area later has to be cleared."
            ),
            lsr_tag="Work Authorisation",
            dedupe_key=f"{camera_id}:crowd_surge",
            hazard_class="behaviour",
        ))

    return drafts


# ---------------------------------------------------------------------------
# Detection-level rules (zone access, vehicle proximity)
# ---------------------------------------------------------------------------
def _zone_rules(persons: list[DetectedObject], camera: dict) -> list[EventDraft]:
    camera_id = camera.get("camera_id", "")
    drafts: list[EventDraft] = []
    for person in persons:
        fx, fy = _feet(person)
        for roi in camera.get("rois", []):
            roi_type = roi.get("roi_type")
            if roi_type not in ("restricted_zone", "lifting_zone"):
                continue
            if not _point_in_polygon(fx, fy, roi["points"]):
                continue

            is_restricted = roi_type == "restricted_zone"
            event_type = "restricted_zone_entry" if is_restricted else "lifting_zone_entry"
            zone_label = "restricted zone" if is_restricted else "lifting/exclusion zone"
            inference = (
                f"Possible exposure to a hazardous area ({roi['hazard_context']}). Verify the "
                "person is authorised and that the area controls are in place."
                if is_restricted
                else "Possible exposure to a suspended-load or line-of-fire hazard."
            )
            drafts.append(EventDraft(
                event_type=event_type,
                severity="high",
                confidence=round(person.confidence, 3),
                objects=[person],
                evidence=(
                    f"person ground point ({fx:.3f}, {fy:.3f}) inside ROI "
                    f"{roi['name']!r}, detection confidence {person.confidence:.2f}"
                ),
                roi=roi["name"],
                observed=f"A person was standing inside the configured {zone_label} {roi['name']!r}.",
                inference=inference,
                sif_relevance=(
                    "Requires HSE review - zone-access control potentially breached while the "
                    "hazard energy in that area was live."
                ),
                lsr_tag=roi["lsr_tag"],
                dedupe_key=f"{camera_id}:{event_type}:{roi['name']}",
                hazard_class="zone",
            ))
    return drafts


def _proximity_rules(
    persons: list[DetectedObject],
    vehicles: list[DetectedObject],
    camera: dict,
) -> list[EventDraft]:
    camera_id = camera.get("camera_id", "")
    drafts: list[EventDraft] = []
    for person, vehicle in itertools.product(persons, vehicles):
        dist = _distance(person.center(), vehicle.center())
        if dist >= PROXIMITY_THRESHOLD:
            continue
        drafts.append(EventDraft(
            event_type="vehicle_person_proximity",
            severity="high" if dist < PROXIMITY_THRESHOLD * 0.5 else "medium",
            confidence=round(min(person.confidence, vehicle.confidence), 3),
            objects=[person, vehicle],
            evidence=(
                f"person-to-{vehicle.class_name} centre distance {dist:.3f} "
                f"(threshold {PROXIMITY_THRESHOLD})"
            ),
            roi=None,
            observed=f"A person and a {vehicle.class_name} were detected in close proximity.",
            inference=(
                "Possible vehicle-person interaction / struck-by exposure. Confirm a "
                "banksman is controlling the movement and that segregation is in place."
            ),
            sif_relevance=(
                "Vehicle-pedestrian interaction is a recognised SIF mechanism on mine and "
                "field sites, and is fatal far more often than it is injurious."
            ),
            lsr_tag="Driving",
            dedupe_key=f"{camera_id}:vehicle_person_proximity",
            hazard_class="proximity",
        ))
    return drafts


def evaluate(
    detections: list[DetectedObject],
    camera: dict,
    signals: Optional[SceneSignals] = None,
) -> list[EventDraft]:
    """Evaluate every rule against one frame, highest severity first.

    `signals` is optional so a caller that only has detections (a unit test,
    or a future batch job over stills) still gets the zone and proximity
    rules rather than an exception.
    """
    persons = [d for d in detections if d.class_name == "person"]
    vehicles = [d for d in detections if d.class_name in VEHICLE_CLASSES]

    drafts: list[EventDraft] = []
    if signals is not None:
        drafts.extend(_scene_rules(signals, camera, persons))
    drafts.extend(_zone_rules(persons, camera))
    drafts.extend(_proximity_rules(persons, vehicles, camera))

    drafts.sort(key=lambda d: (-SEVERITY_ORDER.get(d.severity, 0), -d.confidence))
    return drafts
