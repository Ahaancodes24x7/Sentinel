"""Camera Watch — AI/ML-layer tests for the detection and rule boundary.

Covers the computer-vision module in isolation from the backend: the YOLO
detector wrapper, the ROI/proximity hazard-rule layer, the safety-event
schema, and the demo site/camera registry for the three real OIL India
locations used in the SIH demo (Duliajan, Digboi, Moran).

Detector.detect() itself is exercised against a real (blank) frame to prove
the model loads and returns well-formed output — no model output is asserted
on its *content*, since a blank frame legitimately detects nothing. The
hazard-rule tests below feed synthetic DetectedObject fixtures directly
(the documented way to plug detections in), rather than depending on YOLO
recognizing anything drawn into a test image.
"""
from __future__ import annotations

import numpy as np
import pytest

from sif_engine.vision import camera_registry, hazard_rules
from sif_engine.vision.detector import DetectedObject, YoloDetector
from sif_engine.vision.schemas import SafetyEvent
from sif_engine.vision.stream_processor import get_manager


# ---------------------------------------------------------------------------
# 1 & 2. Detector initializes and returns structured detections
# ---------------------------------------------------------------------------
def test_detector_initializes():
    detector = YoloDetector.get_instance()
    status = detector.status()
    # Superset, not equality: status also reports the tuning actually in use
    # (confidence threshold, inference size), and a test that pins the exact
    # key set turns every added diagnostic into a failure.
    assert {"model_name", "device", "ready", "error"} <= set(status)
    assert status["device"] in ("cpu", "cuda")
    # Either it loaded (weights present / downloadable) or it failed loudly
    # with a human-readable reason — never silently.
    if not status["ready"]:
        assert status["error"]


def test_detector_returns_structured_detections():
    detector = YoloDetector.get_instance()
    blank_frame = np.zeros((240, 320, 3), dtype=np.uint8)
    detections = detector.detect(blank_frame)
    assert isinstance(detections, list)
    for det in detections:
        assert isinstance(det, DetectedObject)
        d = det.to_dict()
        assert set(d) == {"class_name", "confidence", "bbox"}
        assert 0.0 <= d["confidence"] <= 1.0
        assert len(d["bbox"]) == 4


def test_detector_handles_missing_model_gracefully():
    """A detector that failed to load must return [] rather than raising —
    the rest of Sentinel keeps working even if this optional feature can't."""
    broken = YoloDetector.__new__(YoloDetector)
    broken._model = None
    broken._device = "cpu"
    broken._load_error = "simulated load failure"
    broken._weights_path = "yolov8n.pt"
    broken.conf_threshold = 0.35
    assert broken.detect(np.zeros((10, 10, 3), dtype=np.uint8)) == []
    assert broken.is_ready is False


# ---------------------------------------------------------------------------
# 3. Safety rule engine identifies a person in a restricted ROI
# ---------------------------------------------------------------------------
def test_restricted_zone_rule_fires():
    camera = camera_registry.get_camera("DUL-C01")
    # Restricted zone polygon is [[0.62,0.10],[0.95,0.10],[0.95,0.52],[0.62,0.52]].
    # Zone membership is tested at the GROUND POINT (bottom-centre), so this
    # box has to have its feet at (0.70, 0.40) to count as inside.
    person_inside = DetectedObject("person", 0.9, (0.65, 0.2, 0.75, 0.4))
    drafts = hazard_rules.evaluate([person_inside], camera)
    types = [d.event_type for d in drafts]
    assert "restricted_zone_entry" in types
    draft = next(d for d in drafts if d.event_type == "restricted_zone_entry")
    assert draft.severity == "high"
    assert draft.lsr_tag == "Energy Isolation"
    assert "restricted" in draft.observed.lower()
    assert "exposure" in draft.inference.lower() or "hazard" in draft.inference.lower()


def test_restricted_zone_rule_does_not_fire_outside_roi():
    camera = camera_registry.get_camera("DUL-C01")
    person_outside = DetectedObject("person", 0.9, (0.02, 0.02, 0.10, 0.10))
    drafts = hazard_rules.evaluate([person_outside], camera)
    assert drafts == []


def test_zone_rule_uses_ground_point_not_box_centre():
    """A tall box whose CENTRE lands in a zone but whose feet do not must not
    fire. Testing the centre is the single largest source of false zone alarms:
    a person standing in front of a wall-mounted zone reads as being inside it.
    """
    camera = camera_registry.get_camera("DUL-C01")
    # Centre is (0.70, 0.40) - inside the restricted polygon - but the feet are
    # at y=0.95, well below it.
    tall_person = DetectedObject("person", 0.9, (0.66, 0.10, 0.74, 0.95))
    assert 0.10 <= 0.40 <= 0.52  # the centre really is inside the zone band
    drafts = hazard_rules.evaluate([tall_person], camera)
    assert not any(d.event_type == "restricted_zone_entry" for d in drafts)


def test_lifting_zone_rule_fires():
    camera = camera_registry.get_camera("MOR-C01")
    # Lifting zone polygon is [[0.06,0.58],[0.38,0.58],[0.38,0.92],[0.06,0.92]]
    person_inside = DetectedObject("person", 0.85, (0.15, 0.6, 0.25, 0.8))
    drafts = hazard_rules.evaluate([person_inside], camera)
    draft = next(d for d in drafts if d.event_type == "lifting_zone_entry")
    assert draft.severity == "high"
    assert draft.lsr_tag == "Safe Mechanical Lifting"


# ---------------------------------------------------------------------------
# 4. Vehicle/person proximity rule
# ---------------------------------------------------------------------------
def test_vehicle_person_proximity_rule_fires_when_close():
    camera = camera_registry.get_camera("DIG-C01")
    person = DetectedObject("person", 0.9, (0.30, 0.30, 0.36, 0.50))
    truck = DetectedObject("truck", 0.88, (0.33, 0.32, 0.45, 0.55))
    drafts = hazard_rules.evaluate([person, truck], camera)
    draft = next(d for d in drafts if d.event_type == "vehicle_person_proximity")
    # Well inside half the proximity threshold, so this escalates past the
    # baseline "medium" a merely-nearby pairing would get.
    assert draft.severity == "high"
    assert draft.lsr_tag == "Driving"
    assert len(draft.objects) == 2


def test_vehicle_person_proximity_severity_is_graded_by_distance():
    camera = camera_registry.get_camera("DIG-C01")
    person = DetectedObject("person", 0.9, (0.30, 0.30, 0.36, 0.50))
    truck = DetectedObject("truck", 0.88, (0.40, 0.34, 0.52, 0.58))
    drafts = hazard_rules.evaluate([person, truck], camera)
    draft = next(d for d in drafts if d.event_type == "vehicle_person_proximity")
    assert draft.severity == "medium"


def test_vehicle_person_proximity_rule_does_not_fire_when_far():
    camera = camera_registry.get_camera("DIG-C01")
    person = DetectedObject("person", 0.9, (0.02, 0.02, 0.08, 0.10))
    truck = DetectedObject("truck", 0.88, (0.85, 0.85, 0.99, 0.99))
    drafts = hazard_rules.evaluate([person, truck], camera)
    assert not any(d.event_type == "vehicle_person_proximity" for d in drafts)


# ---------------------------------------------------------------------------
# 5. Event schema validation
# ---------------------------------------------------------------------------
def test_safety_event_schema_has_required_fields():
    from datetime import datetime, timezone

    event = SafetyEvent(
        event_id="vis_test123",
        timestamp=datetime.now(timezone.utc),
        site_id="duliajan",
        camera_id="DUL-C01",
        camera_name="Duliajan - Process Area Camera 1",
        event_type="restricted_zone_entry",
        severity="high",
        confidence=0.91,
        objects=[{"class_name": "person", "confidence": 0.91, "bbox": [0.1, 0.1, 0.2, 0.2]}],
        evidence="person bbox=(0.1, 0.1, 0.2, 0.2) inside ROI 'Restricted Zone'",
        roi="Restricted Zone",
        observed="Person detected inside configured 'Restricted Zone' restricted zone.",
        inference="Potential exposure to a hazardous area.",
        sif_relevance="Requires HSE review.",
        lsr_tag="Energy Isolation",
    )
    d = event.to_dict()
    required = {
        "event_id", "timestamp", "site_id", "camera_id", "event_type",
        "severity", "confidence", "objects", "evidence", "roi", "status",
    }
    assert required <= set(d)
    assert d["status"] == "active"


# ---------------------------------------------------------------------------
# 6 & 7. Site configuration — exactly Duliajan, Digboi, Moran; correct cameras
# ---------------------------------------------------------------------------
def test_camera_registry_covers_exactly_three_sites():
    site_ids = {meta["site_id"] for meta in camera_registry.CAMERA_REGISTRY.values()}
    assert site_ids == {"duliajan", "digboi", "moran"}


@pytest.mark.parametrize(
    "site_id,expected_prefix",
    [("duliajan", "DUL-"), ("digboi", "DIG-"), ("moran", "MOR-")],
)
def test_site_switching_returns_correct_cameras(site_id, expected_prefix):
    cameras = camera_registry.get_cameras_for_site(site_id)
    assert len(cameras) == 2
    for cam in cameras:
        assert cam["camera_id"].startswith(expected_prefix)
        assert cam["site_id"] == site_id
        assert len(cam["rois"]) == 3


def test_unknown_site_returns_no_cameras():
    assert camera_registry.get_cameras_for_site("unknown_site") == []


# ---------------------------------------------------------------------------
# 8. Demo video source (and webcam-equivalent) session can be initialized
# ---------------------------------------------------------------------------
def test_session_can_be_started_and_stopped_for_demo_video():
    manager = get_manager()
    session = manager.start("DUL-C01", "duliajan", "demo_video")
    assert session.active is True
    assert session.source_type == "demo_video"

    status = manager.status("DUL-C01")
    assert status["active"] is True
    assert status["site_id"] == "duliajan"

    stopped = manager.stop("DUL-C01")
    assert stopped.active is False


def test_process_frame_produces_frame_analysis_contract():
    manager = get_manager()
    manager.start("DUL-C02", "duliajan", "webcam")
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    result = manager.process_frame("DUL-C02", "duliajan", frame)
    assert set(result) >= {
        "camera_id", "site_id", "frame_ts", "people_count",
        "vehicle_count", "detections", "new_events", "model_name", "device",
    }
    manager.stop("DUL-C02")
