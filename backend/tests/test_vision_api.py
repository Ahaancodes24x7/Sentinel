"""Live Safety Vision — backend API integration tests.

Mirrors backend/tests/test_api.py's setup (isolated SQLite unless
DATABASE_URL is set, same demo auth). Only the model-inference boundary is
mocked (YoloDetector.detect on the shared singleton) so the hazard-rule
evaluation, event persistence, and API contract are all exercised for real —
the feature itself is never mocked away.

Tests:
1. GET /vision/cameras covers exactly the three real OIL India demo sites.
2. Site filtering on /vision/cameras returns that site's cameras only.
3. POST /vision/start + /vision/stop lifecycle for a demo_video source.
4. POST /vision/analyze-frame turns a mocked "person in restricted zone"
   detection into a real, persisted, high-severity safety event.
5. GET /vision/events returns the persisted event; acknowledge updates it.
6. GET /vision/status reports live counts and hazard totals from the DB.
7. Existing report-analysis endpoints are unaffected by this module.
"""
import base64
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "aiml", "src")))

if not os.getenv("DATABASE_URL"):
    os.environ["TEST_ISOLATED_SQLITE"] = "1"

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.database import init_db
from backend.main import app
from sif_engine.vision.detector import DetectedObject
from sif_engine.vision.stream_processor import get_manager


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    init_db()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    res = client.post("/api/v1/auth/login", json={"username": "hse_demo", "password": "demo123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _tiny_frame_base64() -> str:
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", frame)
    assert ok
    return base64.b64encode(buf).decode()


def test_vision_cameras_covers_exactly_three_sites(client, auth_headers):
    res = client.get("/api/v1/vision/cameras", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    site_ids = {c["site_id"] for c in body["cameras"]}
    assert site_ids == {"duliajan", "digboi", "moran"}
    assert len(body["cameras"]) == 6
    assert "demo_notice" in body


def test_vision_cameras_filtered_by_site(client, auth_headers):
    res = client.get("/api/v1/vision/cameras", params={"site_id": "moran"}, headers=auth_headers)
    assert res.status_code == 200
    cams = res.json()["cameras"]
    assert len(cams) == 2
    assert all(c["camera_id"].startswith("MOR-") for c in cams)
    assert all(len(c["rois"]) == 3 for c in cams)


def test_vision_requires_auth(client):
    res = client.get("/api/v1/vision/cameras")
    assert res.status_code == 401


def test_vision_start_and_stop_demo_video_session(client, auth_headers):
    res = client.post(
        "/api/v1/vision/start",
        json={"site_id": "duliajan", "camera_id": "DUL-C01", "source_type": "demo_video"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["active"] is True
    assert body["source_type"] == "demo_video"
    assert "OIL India" in body["demo_notice"]
    assert body["device"] in ("cpu", "cuda")

    stop = client.post("/api/v1/vision/stop", json={"camera_id": "DUL-C01"}, headers=auth_headers)
    assert stop.status_code == 200
    assert stop.json()["active"] is False


def test_vision_start_rtsp_without_url_is_rejected(client, auth_headers):
    res = client.post(
        "/api/v1/vision/start",
        json={"site_id": "duliajan", "camera_id": "DUL-C01", "source_type": "rtsp"},
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_analyze_frame_generates_and_persists_restricted_zone_event(client, auth_headers, monkeypatch):
    """Model-inference boundary mocked: detector.detect is patched to return a
    deterministic person inside DUL-C01's configured restricted ROI, so the
    hazard-rule layer and full API/DB round trip run for real."""
    manager = get_manager()
    detector = manager._get_detector()  # noqa: SLF001 - shared singleton, test needs to patch it
    person_in_restricted_zone = DetectedObject("person", 0.91, (0.65, 0.2, 0.75, 0.4))
    monkeypatch.setattr(detector, "detect", lambda frame: [person_in_restricted_zone])

    client.post(
        "/api/v1/vision/start",
        json={"site_id": "duliajan", "camera_id": "DUL-C01", "source_type": "demo_video"},
        headers=auth_headers,
    )

    res = client.post(
        "/api/v1/vision/analyze-frame",
        json={"site_id": "duliajan", "camera_id": "DUL-C01", "image_base64": _tiny_frame_base64()},
        headers=auth_headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["people_count"] == 1
    assert len(body["new_events"]) == 1

    event = body["new_events"][0]
    assert event["event_type"] == "restricted_zone_entry"
    assert event["severity"] == "high"
    assert event["lsr_tag"] == "Energy Isolation"
    assert event["status"] == "active"
    assert "restricted" in event["observed"].lower()
    assert event["objects"][0]["class_name"] == "person"

    # Persisted: visible via GET /vision/events, independent of in-memory state.
    events_res = client.get(
        "/api/v1/vision/events", params={"camera_id": "DUL-C01"}, headers=auth_headers
    )
    assert events_res.status_code == 200
    stored = events_res.json()["events"]
    assert any(e["event_id"] == event["event_id"] for e in stored)

    # Status reflects the live counts + persisted hazard totals together.
    status_res = client.get(
        "/api/v1/vision/status", params={"camera_id": "DUL-C01"}, headers=auth_headers
    )
    assert status_res.status_code == 200
    status_body = status_res.json()
    assert status_body["active_hazards"] >= 1
    assert status_body["high_priority_hazards"] >= 1

    # Acknowledge updates status and moves the event out of "active".
    ack = client.post(f"/api/v1/vision/events/{event['event_id']}/acknowledge", headers=auth_headers)
    assert ack.status_code == 200
    assert ack.json()["status"] == "acknowledged"
    assert ack.json()["acknowledged_by"] == "hse_demo"

    acked_query = client.get(
        "/api/v1/vision/events",
        params={"camera_id": "DUL-C01", "status": "acknowledged"},
        headers=auth_headers,
    )
    assert any(e["event_id"] == event["event_id"] for e in acked_query.json()["events"])

    client.post("/api/v1/vision/stop", json={"camera_id": "DUL-C01"}, headers=auth_headers)


def test_acknowledge_unknown_event_returns_404(client, auth_headers):
    res = client.post("/api/v1/vision/events/vis_doesnotexist/acknowledge", headers=auth_headers)
    assert res.status_code == 404


def test_analyze_frame_rejects_invalid_image_payload(client, auth_headers):
    res = client.post(
        "/api/v1/vision/analyze-frame",
        json={"site_id": "duliajan", "camera_id": "DUL-C01", "image_base64": "not-valid-base64!!"},
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_existing_report_pipeline_unaffected_by_vision_module(client, auth_headers):
    """Sanity check that mounting the vision routes did not disturb Stage 1/2."""
    res = client.get("/api/v1/health", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    res2 = client.get("/api/v1/sites", headers=auth_headers)
    assert res2.status_code == 200
    site_ids = {s["site_id"] for s in res2.json()["sites"]}
    assert {"duliajan", "digboi", "moran"} <= site_ids
