"""Tests for the scene-analysis half of CCTV hazard monitoring.

These cover what a COCO detector cannot see and what the system is actually
specified to catch: fire, smoke, obscuration, a worker going down, and a mass
falling onto someone - plus the complaint drafting and priority arithmetic
that turn any of those into a filed report.

Frames are synthesised rather than loaded from fixtures so the suite stays
self-contained and deterministic where it can be. Where a signal is genuinely
temporal (flicker, descent speed, time-to-immobility) the test advances a
clock by sleeping briefly rather than pretending one frame is enough - a
version of these tests that passed on a single frame would not be testing the
thing that makes the detector work.
"""
from __future__ import annotations

import time

import cv2
import numpy as np
import pytest

from sif_engine.vision import hazard_rules
from sif_engine.vision.detector import DetectedObject
from sif_engine.vision.incident_report import (
    PRIORITY_P1,
    PRIORITY_P2,
    PRIORITY_P3,
    build_complaint,
    build_narrative,
    derive_priority,
    is_reportable,
)
from sif_engine.vision.scene_analysis import SceneAnalyzer


def _scene(seed: int = 0) -> np.ndarray:
    """A textured industrial-looking background.

    Texture matters: the smoke test compares edge energy inside the plume
    against the frame average, and the visibility analyzer tracks edge energy
    over time. A flat grey frame would make both trivially undefined.
    """
    rng = np.random.RandomState(seed)
    frame = np.zeros((360, 640, 3), np.uint8)
    frame[:, :] = (70, 75, 80)
    frame = cv2.add(frame, np.repeat(rng.randint(0, 40, (360, 640, 1)).astype(np.uint8), 3, axis=2))
    for x in range(0, 640, 40):
        cv2.line(frame, (x, 0), (x, 360), (110, 112, 118), 1)
    for y in range(0, 360, 40):
        cv2.line(frame, (0, y), (640, y), (105, 108, 115), 1)
    return frame


def _flame(frame: np.ndarray, jitter: int) -> np.ndarray:
    """Draw a flame whose outline changes shape frame to frame."""
    rng = np.random.RandomState(jitter)
    cx, cy = 320 + int(rng.randint(-5, 5)), 250
    pts = np.array([
        [cx - 35 + int(rng.randint(-8, 8)), cy],
        [cx + int(rng.randint(-12, 12)), cy - 80 - int(rng.randint(0, 25))],
        [cx + 35 + int(rng.randint(-8, 8)), cy],
    ], np.int32)
    cv2.fillPoly(frame, [pts], (30, 140, 250))
    cv2.fillPoly(frame, [pts + np.array([0, 14])], (60, 200, 255))
    return frame


# ---------------------------------------------------------------------------
# Fire
# ---------------------------------------------------------------------------
def test_flickering_flame_is_detected():
    analyzer = SceneAnalyzer()
    fired_at = None
    for i in range(16):
        frame = _scene(i % 3)
        if i >= 5:
            frame = _flame(frame, i)
        signals = analyzer.analyze(frame, [])
        if signals.fire_active and fired_at is None:
            fired_at = i
    assert fired_at is not None, "a flickering flame must raise the fire signal"
    # Within a few frames of ignition, not thirty - a fire alarm that needs ten
    # seconds of steady burning has missed the point.
    assert fired_at <= 9
    assert signals.fire_score > 0.2
    assert signals.fire_regions, "the console needs to know WHERE the flame is"


def test_static_orange_object_does_not_read_as_fire():
    """Hi-vis PPE, painted plant and sodium lighting are all flame-coloured.

    Colour alone cannot separate them from a fire; only the flicker test can,
    so this is the case that keeps the fire alarm usable on a real site.
    """
    analyzer = SceneAnalyzer()
    ever_active = False
    for i in range(20):
        frame = _scene(i % 3)
        cv2.rectangle(frame, (280, 180), (360, 300), (30, 140, 250), -1)
        signals = analyzer.analyze(frame, [])
        ever_active = ever_active or signals.fire_active
    assert ever_active is False
    assert signals.fire_score < 0.25


# ---------------------------------------------------------------------------
# Smoke and visibility
# ---------------------------------------------------------------------------
def _plume(frame: np.ndarray, age: int) -> np.ndarray:
    """Composite a soft, rising, semi-transparent plume onto a frame.

    Deliberately diffuse. Smoke has no hard edges and it VEILS the detail
    behind it, which is exactly what the texture test keys on; a fixture drawn
    with crisp filled circles is EDGIER than the background it sits on, so it
    tests the opposite of the thing being detected and would only pass by
    accident.
    """
    h, w = frame.shape[:2]
    mask = np.zeros((h, w), np.float32)
    for k in range(4):
        radius = 22 + age * 7 + k * 14
        cy = int(h * 0.62) - age * 9 - k * 20
        cv2.circle(mask, (int(w * 0.5) + k * 6, cy), radius, 1.0, -1)
    mask = cv2.GaussianBlur(mask, (0, 0), 20)
    mask = np.clip(mask * (0.5 + age * 0.05), 0, 0.9)[:, :, None]
    colour = np.full_like(frame, (170, 174, 178), dtype=np.uint8)
    return (frame.astype(np.float32) * (1 - mask) + colour.astype(np.float32) * mask).astype(np.uint8)


def test_growing_smoke_plume_is_detected():
    analyzer = SceneAnalyzer()
    fired_at = None
    for i in range(22):
        frame = _scene(i % 3)
        if i >= 5:
            frame = _plume(frame, i - 5)
        signals = analyzer.analyze(frame, [])
        if signals.smoke_active and fired_at is None:
            fired_at = i
    assert fired_at is not None, "a spreading grey plume must raise the smoke signal"
    assert signals.smoke_score > 0.2
    assert signals.visibility < 1.0, "a plume must also register as lost scene detail"


def test_static_grey_scene_is_not_a_plume():
    """An underground scene is almost entirely desaturated.

    Grey alone therefore says nothing, and a detector keyed on colour would
    report the whole frame as smoke on every camera in the mine.
    """
    analyzer = SceneAnalyzer()
    for i in range(18):
        frame = _scene(0)  # identical frame every time: grey, and going nowhere
        signals = analyzer.analyze(frame, [])
        assert signals.smoke_active is False
        assert signals.smoke_score < 0.1


def test_detected_people_are_cut_out_of_the_smoke_mask():
    """A worker in a grey overall is desaturated and moving, which is most of
    the smoke test. Excluding detection boxes is what stops every person on
    site from raising a plume alarm."""
    analyzer = SceneAnalyzer()
    ever_active = False
    for i in range(18):
        frame = _scene(i % 3)
        # A large grey shape shuffling across the frame.
        x = 120 + i * 12
        cv2.rectangle(frame, (x, 120), (x + 150, 340), (150, 152, 155), -1)
        person = DetectedObject("person", 0.9, (x / 640, 120 / 360, (x + 150) / 640, 340 / 360))
        signals = analyzer.analyze(frame, [person])
        ever_active = ever_active or signals.smoke_active
    assert ever_active is False


# ---------------------------------------------------------------------------
# Person down
# ---------------------------------------------------------------------------
def test_person_falling_then_lying_still_raises_fall_then_immobile():
    analyzer = SceneAnalyzer()
    upright = (0.42, 0.20, 0.54, 0.75)
    prone = (0.40, 0.56, 0.70, 0.74)
    boxes = [upright] * 3 + [prone] * 9

    kinds: list[str] = []
    for i, box in enumerate(boxes):
        frame = _scene(i % 3)
        cv2.rectangle(
            frame,
            (int(box[0] * 640), int(box[1] * 360)),
            (int(box[2] * 640), int(box[3] * 360)),
            (120, 130, 140), -1,
        )
        signals = analyzer.analyze(frame, [DetectedObject("person", 0.9, box)])
        kinds.extend(f.kind for f in signals.falls)
        time.sleep(0.4)

    assert "fall" in kinds, "an upright-to-prone transition must raise a fall"
    assert "immobile" in kinds, "staying down must escalate to a man-down signal"
    # Debounced, not repeated on every subsequent frame.
    assert kinds.count("fall") == 1
    assert kinds.count("immobile") == 1


def test_person_standing_still_is_not_a_fall():
    analyzer = SceneAnalyzer()
    box = (0.42, 0.20, 0.54, 0.75)
    for i in range(10):
        frame = _scene(i % 3)
        cv2.rectangle(frame, (269, 72), (346, 270), (120, 130, 140), -1)
        signals = analyzer.analyze(frame, [DetectedObject("person", 0.9, box)])
        assert signals.falls == []
        time.sleep(0.3)


# ---------------------------------------------------------------------------
# Falling mass
# ---------------------------------------------------------------------------
def test_mass_descending_onto_a_person_is_detected_as_an_impact():
    analyzer = SceneAnalyzer()
    person = (0.45, 0.45, 0.55, 0.90)
    hits = []
    for i in range(12):
        frame = _scene(i % 3)
        cv2.rectangle(frame, (288, 162), (352, 324), (120, 130, 140), -1)
        if i >= 4:
            oy = 0.02 + (i - 4) * 0.11
            cv2.rectangle(
                frame,
                (int(0.44 * 640), int(oy * 360)),
                (int(0.52 * 640), int((oy + 0.07) * 360)),
                (40, 55, 70), -1,
            )
        signals = analyzer.analyze(frame, [DetectedObject("person", 0.9, person)])
        hits.extend(signals.falling_objects)
        time.sleep(0.35)

    assert hits, "a mass descending onto a worker must be detected"
    assert any(h.near_person for h in hits)
    assert all(h.descent_speed > 0 for h in hits)


def test_flame_motion_does_not_register_as_a_falling_mass():
    """A flame front churns, so its motion blobs look like moving masses.

    Without excluding flagged fire regions from the blob search, every fire
    would also raise a spurious roof-fall alarm next to the real fire alarm.
    """
    analyzer = SceneAnalyzer()
    falling = []
    for i in range(16):
        frame = _scene(i % 3)
        if i >= 4:
            frame = _flame(frame, i)
        signals = analyzer.analyze(frame, [])
        falling.extend(signals.falling_objects)
        time.sleep(0.25)
    assert falling == []


# ---------------------------------------------------------------------------
# Rules over signals
# ---------------------------------------------------------------------------
def _camera() -> dict:
    return {"camera_id": "DUL-C01", "camera_name": "Test Camera", "site_id": "duliajan", "rois": []}


def test_fire_signal_produces_a_critical_event_when_people_are_present():
    analyzer = SceneAnalyzer()
    signals = None
    for i in range(14):
        frame = _flame(_scene(i % 3), i) if i >= 4 else _scene(i % 3)
        signals = analyzer.analyze(frame, [])
    assert signals.fire_active

    person = DetectedObject("person", 0.9, (0.1, 0.4, 0.2, 0.9))
    drafts = hazard_rules.evaluate([person], _camera(), signals)
    fire = next(d for d in drafts if d.event_type == "fire_detected")
    assert fire.severity == "critical"
    assert fire.lsr_tag == "Hot Work"
    assert fire.auto_report is True
    assert fire.regions, "the event must carry the flame region for the overlay"
    # Observation and inference stay separate - the observation may not assert
    # that there is a fire, only that a flame-coloured flickering source was seen.
    assert "probable" in fire.inference.lower()
    assert "probable" not in fire.observed.lower()


def test_events_are_ordered_most_severe_first():
    analyzer = SceneAnalyzer()
    signals = None
    for i in range(14):
        frame = _flame(_scene(i % 3), i) if i >= 4 else _scene(i % 3)
        signals = analyzer.analyze(frame, [])

    person = DetectedObject("person", 0.9, (0.66, 0.30, 0.74, 0.45))
    camera = _camera()
    camera["rois"] = [{
        "name": "Restricted Zone",
        "roi_type": "restricted_zone",
        "points": [[0.62, 0.10], [0.95, 0.10], [0.95, 0.52], [0.62, 0.52]],
        "hazard_context": "test area",
        "lsr_tag": "Energy Isolation",
    }]
    drafts = hazard_rules.evaluate([person], camera, signals)
    types = [d.event_type for d in drafts]
    assert "fire_detected" in types and "restricted_zone_entry" in types
    assert types.index("fire_detected") < types.index("restricted_zone_entry")


def test_every_hazard_event_type_is_auto_reportable():
    """No hazard family may be silently non-reporting.

    The operating rule for this feature is that false alarms are acceptable and
    ignored reports are not, so an event type that raised an alarm but filed
    nothing would be a silent regression against it. Each type is also checked
    to have a narrative of its own, since falling back to the generic one loses
    the hazard vocabulary the SIF extraction stage keys on.
    """
    from sif_engine.vision import incident_report

    for event_type in hazard_rules.COOLDOWNS:
        assert is_reportable(event_type)
        assert event_type in incident_report._NARRATIVE, (
            f"{event_type} has no narrative and would file under the generic fallback"
        )


# ---------------------------------------------------------------------------
# Complaint drafting and priority
# ---------------------------------------------------------------------------
def _event(event_type: str, severity: str, confidence: float = 0.8) -> dict:
    return {
        "event_id": "vis_test01",
        "event_type": event_type,
        "severity": severity,
        "confidence": confidence,
        "site_id": "duliajan",
        "camera_id": "DUL-C01",
        "camera_name": "Duliajan - Process Area Camera 1",
        "observed": "A flickering flame-coloured source was detected in the camera view.",
        "inference": "Probable open flame / active fire.",
        "evidence": "flame-colour mask over 2.1% of frame with combustion-consistent flicker",
        "roi": None,
        "timestamp": None,
    }


def test_narrative_is_prose_with_recognisable_hazard_vocabulary():
    text = build_narrative(_event("fire_detected", "critical"), site_name="Duliajan")
    assert "Duliajan" in text
    assert "fire" in text.lower() and "open flame" in text.lower()
    # The disclaimer is not optional: nothing in this text was confirmed by a
    # person, and a reviewer has to be able to see that from the report alone.
    assert "generated automatically" in text.lower()
    assert "not yet been confirmed" in text.lower()
    # Long enough for span extraction to have something to work with.
    assert len(text.split()) > 40


def test_complaint_carries_the_source_event_and_a_recommended_action():
    complaint = build_complaint(_event("person_down_immobile", "critical"), site_name="Moran")
    assert complaint["source_event_id"] == "vis_test01"
    assert complaint["source_event_type"] == "person_down_immobile"
    assert complaint["vision_severity"] == "critical"
    assert "rescue" in complaint["recommended_action"].lower()


@pytest.mark.parametrize(
    "severity,sif,pipeline_conf,vision_conf,expected",
    [
        # The camera is certain and the text pipeline is not: the camera wins.
        ("critical", False, 0.10, 0.90, PRIORITY_P1),
        ("high", False, 0.10, 0.90, PRIORITY_P1),
        ("high", False, 0.10, 0.40, PRIORITY_P2),
        # The text pipeline finds SIF potential the camera rated as routine.
        ("medium", True, 0.90, 0.30, PRIORITY_P1),
        ("medium", False, 0.90, 0.30, PRIORITY_P3),
    ],
)
def test_priority_takes_the_stronger_of_the_two_assessments(
    severity, sif, pipeline_conf, vision_conf, expected
):
    priority, rationale = derive_priority(severity, sif, pipeline_conf, vision_conf)
    assert priority == expected
    assert rationale, "an operator must be able to see WHY a priority was chosen"


def test_confident_text_classifier_cannot_downgrade_a_detected_fire():
    """The specific failure this arithmetic exists to prevent.

    A text pipeline that confidently reads the generated narrative as non-SIF
    must not be able to route a critical camera event to a routine log entry.
    """
    priority, _ = derive_priority("critical", sif_potential=False,
                                  pipeline_confidence=0.99, vision_confidence=0.85)
    assert priority == PRIORITY_P1
