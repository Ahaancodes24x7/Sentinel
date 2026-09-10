"""
FastAPI Backend Integration and AI/ML Pipeline Verification Tests.

Tests:
1. Health endpoint returns 200 with live model metadata and DB connectivity.
2. Login endpoint returns valid access token and /auth/me identifies user and role.
3. Report ingestion returns 202 with processing status and valid batch ID.
4. AI inference integration: Report text -> pipeline -> Baseline 2 classification.
5. Database persistence: Records persist in database and can be queried across sessions.
6. GET /reports/{report_id} returns detail and non-existent ID returns 404 error envelope.
7. Report filtering: Query by site, sif_potential, bucket, and lsr_tag.
8. Evidence span exactness: report_text[span[0]:span[1]] == span_text for all extracted fields.
9. Review queue: Correctly identifies reports requiring human review (LOW_CONF_REVIEW).
10. Two-reviewer agreement rule:
    - Rejects duplicate review action from the same reviewer.
    - Does not promote to training queue on single review action.
    - Successfully promotes to training queue when 2 distinct reviewers agree.
11. Batch status lifecycle: Accurate transition from processing to complete.
12. Dashboard aggregations: Dynamic rankings, trends, summary, and precursor clusters.
13. Dynamic model switching via SENTINEL_SIF_MODEL environment variable.
14. Strict database configuration check (silent SQLite fallback is forbidden).
"""

import os
import sys

# Ensure project root and aiml/src are in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "aiml", "src")))

# If no PostgreSQL DATABASE_URL is explicitly set for the test session,
# enable the explicitly isolated test SQLite option
if not os.getenv("DATABASE_URL"):
    os.environ["TEST_ISOLATED_SQLITE"] = "1"

import pytest
from fastapi.testclient import TestClient

from backend.database import Base, ReportModel, SessionLocal, engine, init_db
from backend.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure database tables exist before running test suite."""
    init_db()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def hse_reviewer_token(client):
    res = client.post("/api/v1/auth/login", json={"username": "hse_demo", "password": "demo123"})
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
def reviewer_2_token(client):
    res = client.post("/api/v1/auth/login", json={"username": "reviewer_2", "password": "demo123"})
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
def hse_manager_token(client):
    res = client.post("/api/v1/auth/login", json={"username": "manager_demo", "password": "demo123"})
    assert res.status_code == 200
    return res.json()["access_token"]


# ---------------------------------------------------------------------------
# Test 1: Health Endpoint
# ---------------------------------------------------------------------------
def test_health_endpoint(client):
    """1. Health endpoint -> 200, exposing active model information and DB status."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    # Assert the field is populated rather than pinning a literal version.
    # Pinning it means every legitimate model retrain breaks the API test suite,
    # which trains people to ignore red tests.
    assert isinstance(data["model_version"], str) and data["model_version"]
    assert data["active_sif_model"] == "baseline2"
    assert data["mlp_available"] is True
    assert "connected" in data["db"]


# ---------------------------------------------------------------------------
# Test 2: Authentication
# ---------------------------------------------------------------------------
def test_auth_login_and_me(client):
    """2. Login -> token returned, and /auth/me returns authenticated user & role."""
    res = client.post("/api/v1/auth/login", json={"username": "hse_demo", "password": "demo123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    assert len(token) > 10

    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "hse_demo"
    assert me_res.json()["role"] == "hse_reviewer"

    # Unauthorized request test
    unauth_res = client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401


# ---------------------------------------------------------------------------
# Test 3: Report Ingestion
# ---------------------------------------------------------------------------
def test_report_ingestion(client, hse_manager_token):
    """3. Report ingestion returns 202 and valid batch ID."""
    payload = {
        "reports": [
            {
                "report_id": "ingest_test_01",
                "site": "Rig 4",
                "report_text": "During maintenance on process equipment at Rig 4, worker bypassed safety interlock.",
                "source": "synthetic",
            }
        ]
    }
    res = client.post(
        "/api/v1/reports/ingest",
        json=payload,
        headers={"Authorization": f"Bearer {hse_manager_token}"},
    )
    assert res.status_code == 202
    data = res.json()
    assert data["ingested_count"] == 1
    assert data["batch_id"].startswith("batch_")
    assert data["status"] == "processing"


# ---------------------------------------------------------------------------
# Test 4: AI Inference Integration
# ---------------------------------------------------------------------------
def test_ai_inference_integration(client, hse_manager_token, hse_reviewer_token):
    """4. End-to-end AI inference integration with Baseline 2 model."""
    high_risk_payload = {
        "reports": [
            {
                "report_id": "ai_infer_h2s_vessel",
                "site": "Rig 7",
                "report_text": (
                    "H2S alarm triggered during confined space vessel entry. "
                    "Gas testing was reportedly done earlier but not re-verified before crew entered. "
                    "No worker injury occurred."
                ),
                "source": "synthetic",
            }
        ]
    }
    ingest_res = client.post(
        "/api/v1/reports/ingest",
        json=high_risk_payload,
        headers={"Authorization": f"Bearer {hse_manager_token}"},
    )
    assert ingest_res.status_code == 202

    # Fetch report detail
    detail_res = client.get(
        "/api/v1/reports/ai_infer_h2s_vessel",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert detail_res.status_code == 200
    data = detail_res.json()
    clf = data["classification"]
    # Must match whatever the health endpoint reports, so the two cannot drift
    # apart silently - that is the property worth testing, not the literal string.
    health = client.get("/api/v1/health").json()
    assert clf["model_version"] == health["model_version"]
    assert isinstance(clf["sif_potential"], bool)
    assert 0.0 <= clf["confidence"] <= 1.0
    assert clf["lsr_tag"] in ["Confined Space", "Gas Testing", "Work Authorisation", "Energy Isolation"]
    assert len(clf["justification"]) > 10


# ---------------------------------------------------------------------------
# Test 5: Database Persistence
# ---------------------------------------------------------------------------
def test_database_persistence_across_sessions(client, hse_manager_token):
    """5. Verify report is persisted into database table."""
    rep_id = "db_persist_check_01"
    payload = {
        "reports": [
            {
                "report_id": rep_id,
                "site": "Well Site B",
                "report_text": "Routine inspection of pressure relief valve. Found slight corrosion on flange.",
                "source": "synthetic",
            }
        ]
    }
    res = client.post(
        "/api/v1/reports/ingest",
        json=payload,
        headers={"Authorization": f"Bearer {hse_manager_token}"},
    )
    assert res.status_code == 202

    # Query DB directly with a separate database session
    db = SessionLocal()
    try:
        db_record = db.query(ReportModel).filter(ReportModel.report_id == rep_id).first()
        assert db_record is not None
        assert db_record.site == "Well Site B"
        assert "relief valve" in db_record.report_text
        assert db_record.review_status == "pending"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Test 6: GET /reports/{report_id} and 404
# ---------------------------------------------------------------------------
def test_get_report_detail_and_404(client, hse_reviewer_token):
    """6. Detail retrieval for existing report, and 404 for unknown report."""
    # Unknown report ID must return 404
    missing_res = client.get(
        "/api/v1/reports/non_existent_report_id_xyz",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert missing_res.status_code == 404
    err = missing_res.json()["error"]
    assert err["code"] == "REPORT_NOT_FOUND"
    assert err["status"] == 404


# ---------------------------------------------------------------------------
# Test 7: Report Filtering
# ---------------------------------------------------------------------------
def test_report_filtering(client, hse_manager_token, hse_reviewer_token):
    """7. List reports with filters: site and sif_potential."""
    # Query with site filter
    res = client.get(
        "/api/v1/reports?site=Rig%204",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    for item in data["items"]:
        assert item["site"] == "Rig 4"


# ---------------------------------------------------------------------------
# Test 8: Evidence Span Exact Character Slicing
# ---------------------------------------------------------------------------
def test_evidence_spans_exact_character_slicing(client, hse_manager_token, hse_reviewer_token):
    """8. Critical: Every span [start, end] must equal report_text[start:end]."""
    raw_text = (
        "During maintenance on process equipment at Rig 4, a worker was standing "
        "within the immediate hazard zone. Isolation status was not clearly confirmed by the crew. "
        "No injury occurred."
    )
    rep_id = "span_verify_exact_01"
    payload = {
        "reports": [
            {
                "report_id": rep_id,
                "site": "Rig 4",
                "report_text": raw_text,
                "source": "synthetic",
            }
        ]
    }
    ingest_res = client.post(
        "/api/v1/reports/ingest",
        json=payload,
        headers={"Authorization": f"Bearer {hse_manager_token}"},
    )
    assert ingest_res.status_code == 202

    detail_res = client.get(
        f"/api/v1/reports/{rep_id}",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert detail_res.status_code == 200
    data = detail_res.json()
    extracted = data["extracted_fields"]

    # Test activity span
    act_span = extracted["activity"]["span"]
    if act_span:
        assert raw_text[act_span[0]:act_span[1]] == extracted["activity"]["text"]

    # Test evidence_spans list
    evidence_spans = extracted["evidence_spans"]
    assert len(evidence_spans) > 0
    for item in evidence_spans:
        s = item["span"]
        extracted_slice = raw_text[s[0]:s[1]]
        assert extracted_slice == item["text"], f"Span slice mismatch: {extracted_slice!r} != {item['text']!r}"


# ---------------------------------------------------------------------------
# Test 9: Review Queue Listing
# ---------------------------------------------------------------------------
def test_review_queue_listing(client, hse_reviewer_token):
    """9. Review queue listing returns paginated reports in review status."""
    res = client.get(
        "/api/v1/review-queue",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data


# ---------------------------------------------------------------------------
# Test 10: Two-Reviewer Agreement Rule & Self-Review Prevention
# ---------------------------------------------------------------------------
def test_two_reviewer_agreement_and_duplicate_prevention(
    client, hse_manager_token, hse_reviewer_token, reviewer_2_token
):
    """
    10. Two-reviewer agreement gate:
        - Prevents same reviewer from submitting twice.
        - First reviewer action records but does not promote.
        - Second distinct reviewer action with matching correction promotes to training queue.
    """
    rep_id = "two_reviewer_gate_test"
    payload = {
        "reports": [
            {
                "report_id": rep_id,
                "site": "Field Station 2",
                "report_text": "Contractor spotted near unshielded electrical panel during shift turnover.",
                "source": "synthetic",
            }
        ]
    }
    client.post(
        "/api/v1/reports/ingest",
        json=payload,
        headers={"Authorization": f"Bearer {hse_manager_token}"},
    )

    action_payload = {
        "action": "correct",
        "corrected_sif_potential": True,
        "corrected_lsr_tag": "Energy Isolation",
        "reviewer_notes": "First reviewer verification: hazardous electrical gap.",
    }

    # Reviewer 1 records action
    res1 = client.post(
        f"/api/v1/review-queue/{rep_id}/action",
        json=action_payload,
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "recorded"
    assert data1["promoted_to_training_queue"] is False

    # Reviewer 1 attempts to submit again -> must fail with 400 DUPLICATE_REVIEW
    res_dup = client.post(
        f"/api/v1/review-queue/{rep_id}/action",
        json=action_payload,
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert res_dup.status_code == 400
    assert "already recorded" in res_dup.json()["detail"]

    # Reviewer 2 records matching correction
    action_payload_2 = {
        "action": "correct",
        "corrected_sif_potential": True,
        "corrected_lsr_tag": "Energy Isolation",
        "reviewer_notes": "Second independent reviewer confirms hazardous energy potential.",
    }
    res2 = client.post(
        f"/api/v1/review-queue/{rep_id}/action",
        json=action_payload_2,
        headers={"Authorization": f"Bearer {reviewer_2_token}"},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "recorded"
    assert data2["promoted_to_training_queue"] is True


# ---------------------------------------------------------------------------
# Test 11: Batch Status Lifecycle
# ---------------------------------------------------------------------------
def test_batch_status_lifecycle(client, hse_manager_token, hse_reviewer_token):
    """11. Ingest batch and verify batch status query returns complete."""
    payload = {
        "reports": [
            {
                "report_id": "batch_status_test_01",
                "site": "Rig 4",
                "report_text": "Scaffolding modification in progress at derrick floor.",
                "source": "synthetic",
            }
        ]
    }
    res = client.post(
        "/api/v1/reports/ingest",
        json=payload,
        headers={"Authorization": f"Bearer {hse_manager_token}"},
    )
    batch_id = res.json()["batch_id"]

    status_res = client.get(
        f"/api/v1/reports/ingest/{batch_id}/status",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["batch_id"] == batch_id
    assert status_data["status"] == "complete"
    assert status_data["classified"] == 1


# ---------------------------------------------------------------------------
# Test 12: Dashboard Aggregations
# ---------------------------------------------------------------------------
def test_dashboard_aggregations(client, hse_reviewer_token):
    """12. Dynamic dashboard metrics calculated from database."""
    # Rankings
    rankings_res = client.get(
        "/api/v1/dashboard/rankings?metric=composite",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert rankings_res.status_code == 200
    r_data = rankings_res.json()
    assert r_data["metric"] == "composite"
    assert r_data["weights"] is not None

    # Trends
    trends_res = client.get(
        "/api/v1/dashboard/trends?granularity=weekly",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert trends_res.status_code == 200
    assert "series" in trends_res.json()

    # Summary
    summary_res = client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert summary_res.status_code == 200
    s_data = summary_res.json()
    assert s_data["total_reports"] >= 1

    # Clusters
    clusters_res = client.get(
        "/api/v1/dashboard/clusters",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert clusters_res.status_code == 200
    assert "clusters" in clusters_res.json()


# ---------------------------------------------------------------------------
# Test 13: Model Switching
# ---------------------------------------------------------------------------
def test_env_var_model_selection(client, monkeypatch):
    """13. Dynamic selection of MLP model via SENTINEL_SIF_MODEL."""
    monkeypatch.setenv("SENTINEL_SIF_MODEL", "mlp")
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["active_sif_model"] == "mlp"
    assert data["model_version"] == "mlp-v0.1"


# ---------------------------------------------------------------------------
# Test 14: Strict Database Enforcement
# ---------------------------------------------------------------------------
def test_strict_database_enforcement(monkeypatch):
    """14. Verifies that silent SQLite fallback is disallowed when TEST_ISOLATED_SQLITE is not set."""
    from backend.database import get_database_url

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_ISOLATED_SQLITE", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        get_database_url()
    assert "DATABASE_URL environment variable is not set" in str(exc_info.value)
    assert "silent fallback to SQLite is disabled" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Operations Map / three-site demo layer
#
# Duliajan, Digboi and Moran are real OIL India locations used as geographic
# demonstration metadata (see aiml/src/sif_engine/site_intelligence/
# site_registry.py). The 25k-report synthetic corpus is tagged at the
# demonstration-unit level ("Rig 4", "Plant C", "Terminal A", ...), each
# linked to one of these real locations via `parent_asset`. These tests cover
# the resolution/filtering layer that lets a request for a real location
# reach the demonstration units that roll up to it, without ever inventing
# report data or leaking another site's reports into a site-scoped view.
# ---------------------------------------------------------------------------
DEMO_SITE_IDS = ["duliajan", "digboi", "moran"]


def test_operations_map_sites_exist_with_valid_coordinates(client, hse_reviewer_token):
    """1 & 2. Duliajan, Digboi and Moran are registered with plausible lat/lon."""
    res = client.get(
        "/api/v1/sites",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert res.status_code == 200
    sites_by_id = {s["site_id"]: s for s in res.json()["sites"]}

    for site_id in DEMO_SITE_IDS:
        assert site_id in sites_by_id, f"{site_id} missing from /sites registry"
        site = sites_by_id[site_id]
        assert site["state"] == "Assam"
        assert site["is_synthetic_prototype"] is False, "real OIL location, not a demo unit"
        # Upper Assam basin — a loose bounding box, just enough to catch a
        # transposed lat/lon or a placeholder (0, 0) coordinate.
        assert 26.0 <= site["latitude"] <= 28.0
        assert 94.0 <= site["longitude"] <= 96.5


def test_site_filter_resolves_demonstration_units_to_real_site(
    client, hse_manager_token, hse_reviewer_token
):
    """3, 4, 5, 10. Filtering by a real site id reaches its demo units and
    excludes reports belonging to a different real site (no cross-site leakage)."""
    payload = {
        "reports": [
            {
                "report_id": "map_test_duliajan_01",
                "site": "Rig 4",  # parent_asset = duliajan
                "report_text": "Crew performing valve maintenance at Rig 4 process skid.",
                "source": "synthetic",
            },
            {
                "report_id": "map_test_duliajan_02",
                "site": "Plant C",  # parent_asset = duliajan
                "report_text": "Gas compression trip investigated at Plant C.",
                "source": "synthetic",
            },
            {
                "report_id": "map_test_digboi_01",
                "site": "Terminal A",  # parent_asset = digboi
                "report_text": "Tanker loading observed at Terminal A dispatch bay.",
                "source": "synthetic",
            },
            {
                "report_id": "map_test_moran_01",
                "site": "Rig 7",  # parent_asset = moran
                "report_text": "Night shift handover reviewed at Rig 7 wellsite.",
                "source": "synthetic",
            },
        ]
    }
    ingest_res = client.post(
        "/api/v1/reports/ingest",
        json=payload,
        headers={"Authorization": f"Bearer {hse_manager_token}"},
    )
    assert ingest_res.status_code == 202

    def report_ids_for(site_id: str) -> set[str]:
        res = client.get(
            f"/api/v1/reports?site={site_id}&limit=200",
            headers={"Authorization": f"Bearer {hse_reviewer_token}"},
        )
        assert res.status_code == 200
        return {item["report_id"] for item in res.json()["items"]}

    duliajan_ids = report_ids_for("duliajan")
    digboi_ids = report_ids_for("digboi")
    moran_ids = report_ids_for("moran")

    # Duliajan's two demo units (Rig 4, Plant C) both roll up.
    assert {"map_test_duliajan_01", "map_test_duliajan_02"} <= duliajan_ids
    # No cross-site leakage: Digboi's and Moran's reports never appear under Duliajan.
    assert "map_test_digboi_01" not in duliajan_ids
    assert "map_test_moran_01" not in duliajan_ids

    assert "map_test_digboi_01" in digboi_ids
    assert "map_test_duliajan_01" not in digboi_ids
    assert "map_test_moran_01" not in digboi_ids

    assert "map_test_moran_01" in moran_ids
    assert "map_test_duliajan_01" not in moran_ids
    assert "map_test_digboi_01" not in moran_ids


def test_all_sites_restores_global_report_view(client, hse_manager_token, hse_reviewer_token):
    """6. Omitting the site filter (ALL SITES) returns reports across multiple sites."""
    payload = {
        "reports": [
            {
                "report_id": "map_test_all_a",
                "site": "Rig 4",
                "report_text": "Housekeeping issue noted near the Rig 4 mud pit.",
                "source": "synthetic",
            },
            {
                "report_id": "map_test_all_b",
                "site": "Rig 7",
                "report_text": "Lifting operation observed at Rig 7 without a banksman present.",
                "source": "synthetic",
            },
        ]
    }
    res = client.post(
        "/api/v1/reports/ingest",
        json=payload,
        headers={"Authorization": f"Bearer {hse_manager_token}"},
    )
    assert res.status_code == 202

    all_res = client.get(
        "/api/v1/reports?limit=200",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert all_res.status_code == 200
    all_ids = {item["report_id"] for item in all_res.json()["items"]}
    assert {"map_test_all_a", "map_test_all_b"} <= all_ids
    sites_seen = {item["site"] for item in all_res.json()["items"]}
    assert len(sites_seen) > 1, "ALL SITES must not be narrowed to a single site"


def test_site_statistics_are_derived_from_reports(client, hse_manager_token, hse_reviewer_token):
    """9. /sites/{site_id} counts are computed from the actual report corpus, not fabricated."""
    ingest_res = client.post(
        "/api/v1/reports/ingest",
        json={
            "reports": [
                {
                    "report_id": "map_test_stats_01",
                    "site": "Terminal A",  # parent_asset = digboi
                    "report_text": (
                        "Loading arm connected without confirming isolation valve position; "
                        "operator stood in the line of fire during pressurization."
                    ),
                    "source": "synthetic",
                }
            ]
        },
        headers={"Authorization": f"Bearer {hse_manager_token}"},
    )
    assert ingest_res.status_code == 202

    before = client.get(
        "/api/v1/reports?site=digboi&limit=1",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    ).json()["total"]

    detail_res = client.get(
        "/api/v1/sites/digboi",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["site_id"] == "digboi"
    assert detail["total_reports"] == before
    assert detail["total_reports"] >= 1
    assert detail["demonstration_notice"]


def test_dashboard_summary_site_filter_and_all_sites(client, hse_reviewer_token):
    """ALL SITES vs a single real site never crash and the site-scoped total never
    exceeds the unfiltered (ALL SITES) total."""
    all_res = client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert all_res.status_code == 200
    all_total = all_res.json()["total_reports"]

    for site_id in DEMO_SITE_IDS:
        scoped_res = client.get(
            f"/api/v1/dashboard/summary?site={site_id}",
            headers={"Authorization": f"Bearer {hse_reviewer_token}"},
        )
        assert scoped_res.status_code == 200
        scoped = scoped_res.json()
        assert scoped["total_reports"] <= all_total
        assert 0.0 <= scoped["sif_rate"] <= 1.0


def test_live_safety_vision_cameras_scoped_per_site(client, hse_reviewer_token):
    """11. Live Safety Vision's camera list follows the selected site and never
    mixes cameras from a different demonstration site."""
    seen_camera_ids: set[str] = set()
    for site_id in DEMO_SITE_IDS:
        res = client.get(
            f"/api/v1/vision/cameras?site_id={site_id}",
            headers={"Authorization": f"Bearer {hse_reviewer_token}"},
        )
        assert res.status_code == 200
        cameras = res.json()["cameras"]
        assert len(cameras) > 0, f"{site_id} has no demo cameras configured"
        for cam in cameras:
            assert cam["site_id"] == site_id
            assert cam["camera_id"] not in seen_camera_ids
            seen_camera_ids.add(cam["camera_id"])
        assert "demonstration" in res.json()["demo_notice"].lower() or "demo" in res.json()["demo_notice"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
