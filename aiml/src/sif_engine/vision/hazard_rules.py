"""Safety-event rule layer for Live Safety Vision.

A pretrained YOLO model only reports "there is a person here, a truck
there" - it has no notion of a restricted zone, and a person standing near a
truck is not, to the model, a hazard. This module is what turns raw object
detections into safety-relevant events, by testing them against the
configured ROI polygons for the camera (see camera_registry.py).

Every rule keeps OBSERVATION separate from INFERENCE:
  - observed  = literally what the detector saw (object + zone / proximity)
  - inference = the safety interpretation a human still has to confirm

PPE (helmet/vest) detection is deliberately NOT implemented here. The
pretrained COCO-class YOLO model this project ships does not detect PPE, and
hallucinating a "helmet missing" event from a model that cannot see helmets
would be exactly the kind of dishonest claim the brief warns against. A
dedicated PPE model could be plugged in by adding a rule function that reads
from a separate detector output - the `evaluate()` signature below already
takes a plain detections list, so that would not require restructuring this
module.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Optional

from .detector import DetectedObject

VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle"}

# Normalized distance between bbox centers below which a person and a
# vehicle are considered "in close proximity". Frame-diagonal-relative, so it
# behaves consistently across different capture resolutions.
PROXIMITY_THRESHOLD = 0.18

# Debounce: without this, a person standing in a zone for 10 seconds at ~2
# fps would create ~20 duplicate events instead of one that stays "active"
# until acknowledged.
EVENT_COOLDOWN_SECONDS = 8.0


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


def evaluate(detections: list[DetectedObject], camera: dict) -> list[EventDraft]:
    """Evaluate configured ROI + proximity rules against one frame's detections."""
    persons = [d for d in detections if d.class_name == "person"]
    vehicles = [d for d in detections if d.class_name in VEHICLE_CLASSES]
    rois = camera.get("rois", [])
    camera_id = camera.get("camera_id", "")
    drafts: list[EventDraft] = []

    for person in persons:
        cx, cy = person.center()
        for roi in rois:
            roi_type = roi.get("roi_type")
            if roi_type not in ("restricted_zone", "lifting_zone"):
                continue
            if not _point_in_polygon(cx, cy, roi["points"]):
                continue

            is_restricted = roi_type == "restricted_zone"
            event_type = "restricted_zone_entry" if is_restricted else "lifting_zone_entry"
            zone_label = "restricted zone" if is_restricted else "lifting/exclusion zone"
            inference = (
                f"Potential exposure to a hazardous area ({roi['hazard_context']})."
                if is_restricted
                else "Potential exposure to a suspended-load / line-of-fire hazard."
            )
            drafts.append(EventDraft(
                event_type=event_type,
                severity="high",
                confidence=round(person.confidence, 3),
                objects=[person],
                evidence=(
                    f"person bbox={tuple(round(v, 3) for v in person.bbox)} "
                    f"inside ROI '{roi['name']}'"
                ),
                roi=roi["name"],
                observed=f"Person detected inside configured '{roi['name']}' {zone_label}.",
                inference=inference,
                sif_relevance="Requires HSE review — zone-access control potentially violated.",
                lsr_tag=roi["lsr_tag"],
                dedupe_key=f"{camera_id}:{event_type}:{roi['name']}",
            ))

    for person, vehicle in itertools.product(persons, vehicles):
        dist = _distance(person.center(), vehicle.center())
        if dist < PROXIMITY_THRESHOLD:
            drafts.append(EventDraft(
                event_type="vehicle_person_proximity",
                severity="medium",
                confidence=round(min(person.confidence, vehicle.confidence), 3),
                objects=[person, vehicle],
                evidence=(
                    f"person-vehicle center distance={round(dist, 3)} "
                    f"(threshold {PROXIMITY_THRESHOLD})"
                ),
                roi=None,
                observed=f"Person and {vehicle.class_name} detected in close proximity.",
                inference="Potential vehicle-person proximity / struck-by hazard.",
                sif_relevance="Requires HSE review — line-of-fire exposure near a vehicle.",
                lsr_tag="Line of Fire",
                dedupe_key=f"{camera_id}:vehicle_person_proximity",
            ))

    return drafts
