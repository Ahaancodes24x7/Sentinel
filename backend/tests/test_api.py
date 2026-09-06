"""
FastAPI Backend Integration and AI/ML Pipeline Verification Tests.

Tests:
1. Health endpoint returns 200 with live model metadata (Baseline 2 default).
2. Login endpoint returns valid access token.
3. Unauthorized access to protected report returns 401.
4. Forbidden role access to audit-log returns 403.
5. Authenticated report detail returns 200 with real model classification.
6. Composite dashboard metric returns 200 and includes weights.
7. Review action submit returns 200 and records action.
8. End-to-end AI inference integration:
   Ingest report -> FastAPI -> sif_engine -> real model artifact -> verified classification.
9. Dynamic model switching via SENTINEL_SIF_MODEL environment variable.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def hse_reviewer_token(client):
    res = client.post("/api/v1/auth/login", json={"username": "hse_demo", "password": "demo123"})
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
def hse_manager_token(client):
    res = client.post("/api/v1/auth/login", json={"username": "manager_demo", "password": "demo123"})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_health_endpoint(client):
    """1. Health endpoint -> 200, exposing active model information."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["model_version"] == "baseline2-v0.3"
    assert data["active_sif_model"] == "baseline2"
    assert data["mlp_available"] is True
    assert data["db"] == "connected"


def test_auth_login_and_me(client):
    """2. Login -> token returned, and /auth/me returns authenticated user."""
    res = client.post("/api/v1/auth/login", json={"username": "hse_demo", "password": "demo123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    assert len(token) > 10

    # Check me endpoint
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "hse_demo"
    assert me_res.json()["role"] == "hse_reviewer"


def test_unauthorized_report_request(client):
    """3. Unauthorized report request -> 401."""
    res = client.get("/api/v1/reports")
    assert res.status_code == 401
    assert "Authorization" in res.json()["detail"]


def test_role_forbidden_audit_request(client, hse_reviewer_token):
    """4. Role-forbidden audit request (hse_reviewer trying to access auditor route) -> 403."""
    res = client.get(
        "/api/v1/audit-log",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert res.status_code == 403
    assert "not permitted" in res.json()["detail"]


def test_authenticated_report_detail_with_real_inference(client, hse_reviewer_token):
    """5. Authenticated report detail -> 200 with real model classification."""
    res = client.get(
        "/api/v1/reports/a1b2c3d4",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["report_id"] == "a1b2c3d4"
    assert "classification" in data
    clf = data["classification"]
    assert isinstance(clf["sif_potential"], bool)
    assert 0.0 <= clf["confidence"] <= 1.0
    assert clf["bucket"] in ["HIGH_CONF_SIF", "LOW_CONF_REVIEW", "HIGH_CONF_NON_SIF", "NEEDS_MORE_INFO"]
    assert isinstance(clf["lsr_tag"], str)
    assert clf["model_version"] == "baseline2-v0.3"
    assert "Flagged as" in clf["justification"]


def test_composite_dashboard_metric(client, hse_reviewer_token):
    """6. Composite dashboard metric -> weights included."""
    # Simple metric without weights
    simple_res = client.get(
        "/api/v1/dashboard/rankings?metric=simple",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert simple_res.status_code == 200
    assert simple_res.json()["weights"] is None

    # Composite metric with weights
    comp_res = client.get(
        "/api/v1/dashboard/rankings?metric=composite",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert comp_res.status_code == 200
    data = comp_res.json()
    assert data["metric"] == "composite"
    assert data["weights"] is not None
    assert "w1_severity_adjusted_rate" in data["weights"]
    assert "w2_recurrence" in data["weights"]
    assert "w3_severity_weighting" in data["weights"]


def test_review_action_accepted(client, hse_reviewer_token):
    """7. Review action -> accepted and recorded."""
    payload = {
        "action": "correct",
        "corrected_sif_potential": True,
        "corrected_lsr_tag": "Energy Isolation",
        "reviewer_notes": "Audited by lead reviewer: verified hazardous energy gap.",
    }
    res = client.post(
        "/api/v1/review-queue/rep_demo_01/action",
        json=payload,
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["report_id"] == "rep_demo_01"
    assert data["status"] == "recorded"
    assert data["promoted_to_training_queue"] is False
    assert data["review_action_id"].startswith("rv_")


def test_ai_inference_end_to_end_pipeline(client, hse_manager_token, hse_reviewer_token):
    """
    8. Critical AI inference integration test:
       sample report -> FastAPI -> sif_engine -> real model artifact -> classification response
    """
    ingest_payload = {
        "reports": [
            {
                "report_id": "rig4_h2s_breach",
                "site": "Rig 4",
                "report_text": (
                    "H2S alarm triggered during confined space vessel entry. "
                    "Gas testing was reportedly done earlier but not re-verified before crew entered. "
                    "No worker injury occurred."
                ),
                "source": "synthetic",
            },
            {
                "report_id": "warehouse_clean",
                "site": "Terminal A",
                "report_text": (
                    "Routine housekeeping completed in warehouse aisles. "
                    "Pallets neatly stacked and emergency exits cleared."
                ),
                "source": "synthetic",
            },
        ]
    }

    # Ingest reports via manager role
    ingest_res = client.post(
        "/api/v1/reports/ingest",
        json=ingest_payload,
        headers={"Authorization": f"Bearer {hse_manager_token}"},
    )
    assert ingest_res.status_code == 202
    batch_id = ingest_res.json()["batch_id"]
    assert ingest_res.json()["ingested_count"] == 2

    # Check batch status
    status_res = client.get(
        f"/api/v1/reports/ingest/{batch_id}/status",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "complete"
    assert status_res.json()["classified"] == 2

    # Fetch classified detail for the high risk report
    detail_res = client.get(
        "/api/v1/reports/rig4_h2s_breach",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["report_id"] == "rig4_h2s_breach"
    assert data["site"] == "Rig 4"

    clf = data["classification"]
    assert clf["model_version"] == "baseline2-v0.3"
    assert isinstance(clf["sif_potential"], bool)
    assert 0.0 <= clf["confidence"] <= 1.0
    assert clf["bucket"] in ["HIGH_CONF_SIF", "LOW_CONF_REVIEW", "HIGH_CONF_NON_SIF"]
    assert clf["lsr_tag"] in ["Confined Space", "Gas Testing", "Work Authorisation", "Energy Isolation"]
    assert len(clf["justification"]) > 10

    # Fetch classified detail for the clean report
    clean_res = client.get(
        "/api/v1/reports/warehouse_clean",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert clean_res.status_code == 200
    clean_data = clean_res.json()
    assert clean_data["classification"]["sif_potential"] is False
    assert clean_data["classification"]["bucket"] == "HIGH_CONF_NON_SIF"


def test_env_var_model_selection(client, monkeypatch):
    """9. Test dynamic selection of MLP model via SENTINEL_SIF_MODEL."""
    monkeypatch.setenv("SENTINEL_SIF_MODEL", "mlp")

    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["active_sif_model"] == "mlp"
    assert data["model_version"] == "mlp-v0.1"


def test_ontology_endpoint(client, hse_reviewer_token):
    """10. Verify ontology endpoint returns ontology structure."""
    res = client.get(
        "/api/v1/ontology",
        headers={"Authorization": f"Bearer {hse_reviewer_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "energy_types" in data


if __name__ == "__main__":
    pytest.main([__file__])
