"""Voice-report ingestion (ESP32 voice node).

The claim these tests defend is the one the whole feature rests on: a spoken
report is not routed by a second, softer classifier. It goes through the same
Stage 0-3 path a typed report takes and earns the same bucket on the same
evidence. If that ever stops being true, the system has two definitions of SIF
potential and the priority shown to a worker means something different from the
priority shown to a reviewer.
"""
import os

os.environ.setdefault("TEST_ISOLATED_SQLITE", "1")

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import Base, engine

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _schema():
    Base.metadata.create_all(bind=engine)
    yield


def _auth() -> dict:
    r = client.post("/api/v1/auth/login", json={"username": "hse_demo", "password": "demo123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


HIGH_ENERGY = (
    "The crane was lifting a pipe joint directly over two workers standing "
    "under the suspended load, there was no barricade and no banksman present"
)
LOW_ENERGY = (
    "The tea room light on the ground floor is flickering and should be "
    "replaced when maintenance next comes around"
)


def _ingest(transcript: str, **over):
    body = {
        "site": "Duliajan",
        "transcript": transcript,
        "device_id": "test-voice-node",
        "asr_confidence": 0.91,
        "asr_model": "faster-whisper-small",
        "asr_language": "en",
        "audio_seconds": 11.4,
        "clip_id": "test.wav",
    }
    body.update(over)
    return client.post("/api/v1/voice/ingest", json=body, headers=_auth())


def test_voice_ingest_requires_auth():
    r = client.post("/api/v1/voice/ingest", json={"site": "Duliajan", "transcript": "x", "device_id": "d"})
    assert r.status_code == 401


def test_high_energy_speech_routes_to_precursor_bucket():
    r = _ingest(HIGH_ENERGY)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["sif_potential"] is True
    assert body["bucket"] == "HIGH_CONF_SIF"
    assert body["lsr_tag"] != "N/A"


def test_low_energy_speech_is_not_inflated_into_a_precursor():
    # The failure mode worth guarding: treating anything spoken into a safety
    # device as urgent. A flickering light is a maintenance note.
    r = _ingest(LOW_ENERGY)
    assert r.status_code == 201, r.text
    assert r.json()["sif_potential"] is False


def test_voice_report_is_stored_as_its_own_source():
    rid = _ingest(HIGH_ENERGY).json()["report_id"]
    detail = client.get(f"/api/v1/reports/{rid}", headers=_auth())
    assert detail.status_code == 200, detail.text
    assert detail.json()["source"] == "voice"


def test_transcript_provenance_reaches_the_console():
    """A reviewer must be able to see that the words are a machine transcript."""
    rid = _ingest(HIGH_ENERGY, asr_confidence=0.42).json()["report_id"]
    detail = client.get(f"/api/v1/reports/{rid}", headers=_auth()).json()
    prov = detail["classification"]["voice_provenance"]
    assert prov is not None
    assert prov["transcript_is_machine_generated"] is True
    assert prov["asr_model"] == "faster-whisper-small"
    # ASR confidence must stay distinct from the SIF confidence - a badly heard
    # recording of an obvious hazard is not a low-confidence hazard call.
    assert prov["asr_confidence"] == pytest.approx(0.42)
    assert detail["classification"]["confidence"] != pytest.approx(0.42)


def test_voice_reports_are_filterable_as_a_source():
    _ingest(HIGH_ENERGY)
    r = client.get("/api/v1/reports", params={"source": "voice", "limit": 50}, headers=_auth())
    assert r.status_code == 200, r.text
    items = r.json().get("items") or r.json().get("reports") or []
    assert items, "voice reports should be retrievable by source"
    # The list response is a summary model and does not carry `source`, so the
    # filter is verified by what it selects rather than by a field on the row.
    for row in items:
        detail = client.get(f"/api/v1/reports/{row['report_id']}", headers=_auth()).json()
        assert detail["source"] == "voice"


def test_spoken_and_typed_reports_get_the_same_verdict():
    """The same words must classify identically whichever door they came in."""
    spoken = _ingest(HIGH_ENERGY).json()
    typed = client.post(
        "/api/v1/reports/submit",
        json={"site": "Duliajan", "report_text": HIGH_ENERGY},
        headers=_auth(),
    )
    assert typed.status_code == 201, typed.text
    typed_clf = typed.json()["classification"]
    assert spoken["bucket"] == typed_clf["bucket"]
    assert spoken["sif_potential"] == typed_clf["sif_potential"]
    assert spoken["lsr_tag"] == typed_clf["lsr_tag"]


def test_existing_report_pipeline_unaffected_by_voice_module():
    """Typed reports must not sprout voice fields."""
    typed = client.post(
        "/api/v1/reports/submit",
        json={"site": "Duliajan", "report_text": LOW_ENERGY},
        headers=_auth(),
    ).json()
    assert typed["source"] == "real"
    assert typed["classification"].get("voice_provenance") is None
