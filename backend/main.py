"""
PS 26165 — FastAPI backend, matching SIH_26165_Backend_API_Specification.md
route-for-route, integrated with sif_engine AI/ML pipeline.

Run with:  uvicorn backend.main:app --reload --port 8000 (from project root)
           or uvicorn main:app --reload --port 8000 (from backend/)
Docs at:   http://localhost:8000/docs
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from pathlib import Path
import yaml

from fastapi import FastAPI, HTTPException, Depends, Header, Query, status
from fastapi.middleware.cors import CORSMiddleware

try:
    from backend.schemas import (
        Bucket, Source, Role, ReviewActionType, PatternType,
        ErrorResponse, ReportIngestRequest, ReportIngestResponse, BatchStatusResponse,
        ReportListItem, PaginatedReports, ExtractedSpanField, ExtractedLabelField,
        ExtractedFields, Classification, ReportDetail,
        RankingRow, MetricWeights, RankingsResponse,
        ClusterItem, ClusterEdge, ClustersResponse,
        TrendPoint, TrendAlert, TrendsResponse, DashboardSummary,
        ReviewActionRequest, ReviewActionResponse,
        EvidenceSummary, RecommendationListItem, RecommendationsResponse,
        EvidenceBreakdown, EvidenceDetail, RecommendedIntervention, RecommendationDetail,
        ActionPlanRequest, ActionPlanResponse, ActionPlanUpdateRequest,
        ImpactBefore, ImpactWeek, ImpactResponse,
        AuditLogEntry, PaginatedAuditLog, HealthResponse,
        LoginRequest, LoginResponse, MeResponse,
    )
except ImportError:
    from schemas import (  # type: ignore
        Bucket, Source, Role, ReviewActionType, PatternType,
        ErrorResponse, ReportIngestRequest, ReportIngestResponse, BatchStatusResponse,
        ReportListItem, PaginatedReports, ExtractedSpanField, ExtractedLabelField,
        ExtractedFields, Classification, ReportDetail,
        RankingRow, MetricWeights, RankingsResponse,
        ClusterItem, ClusterEdge, ClustersResponse,
        TrendPoint, TrendAlert, TrendsResponse, DashboardSummary,
        ReviewActionRequest, ReviewActionResponse,
        EvidenceSummary, RecommendationListItem, RecommendationsResponse,
        EvidenceBreakdown, EvidenceDetail, RecommendedIntervention, RecommendationDetail,
        ActionPlanRequest, ActionPlanResponse, ActionPlanUpdateRequest,
        ImpactBefore, ImpactWeek, ImpactResponse,
        AuditLogEntry, PaginatedAuditLog, HealthResponse,
        LoginRequest, LoginResponse, MeResponse,
    )

from sif_engine.pipeline import run_single, run_batch, get_model_status

app = FastAPI(
    title="PS 26165 — SIF Precursor Detection API",
    version="0.1.0",
    description="Backend API for OIL India SIF-precursor detection & intervention prototype (SIH 2026).",
)

# Wide-open CORS for the hackathon build
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Demo Auth Accounts
# ---------------------------------------------------------------------------
_DEMO_USERS = {
    "hse_demo": {"password": "demo123", "role": Role.hse_reviewer},
    "manager_demo": {"password": "demo123", "role": Role.hse_manager},
    "auditor_demo": {"password": "demo123", "role": Role.auditor},
}
_FAKE_TOKENS: dict[str, Role] = {}  # token -> role


def get_current_role(authorization: Optional[str] = Header(default=None)) -> Role:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    role = _FAKE_TOKENS.get(token)
    if role is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return role


def require_role(*allowed: Role):
    def checker(role: Role = Depends(get_current_role)) -> Role:
        if role not in allowed:
            raise HTTPException(status_code=403, detail=f"Role '{role}' not permitted for this endpoint")
        return role
    return checker


def _now():
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# In-memory storage for ingested reports & batches
# ---------------------------------------------------------------------------
_INGESTED_REPORTS: dict[str, dict[str, Any]] = {}
_BATCH_TRACKER: dict[str, dict[str, Any]] = {}
_AUDIT_LOGS: list[AuditLogEntry] = []
_REVIEW_ACTIONS: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# 1. Ingestion
# ---------------------------------------------------------------------------
@app.post("/api/v1/reports/ingest", response_model=ReportIngestResponse, status_code=202, tags=["ingestion"])
def ingest_reports(payload: ReportIngestRequest, role: Role = Depends(require_role(Role.hse_manager))):
    batch_id = _new_id("batch")

    batch_input = []
    for item in payload.reports:
        rep_id = item.report_id or _new_id("rep")
        batch_input.append({
            "report_id": rep_id,
            "report_text": item.report_text,
            "site": item.site,
            "source": item.source,
        })

    # Dispatch to real sif_engine AI pipeline
    classified_results = run_batch(batch_input)

    for item, res in zip(batch_input, classified_results):
        clf = res["classification"]
        ext = res["extracted_fields"]
        _INGESTED_REPORTS[item["report_id"]] = {
            "report_id": item["report_id"],
            "site": item["site"],
            "timestamp": _now(),
            "source": item.get("source", Source.synthetic),
            "report_text": item["report_text"],
            "extracted_fields": ext,
            "classification": clf,
            "review_status": "pending",
        }

    _BATCH_TRACKER[batch_id] = {
        "total": len(payload.reports),
        "classified": len(classified_results),
        "status": "complete",
    }

    return ReportIngestResponse(ingested_count=len(payload.reports), batch_id=batch_id, status="processing")


@app.get("/api/v1/reports/ingest/{batch_id}/status", response_model=BatchStatusResponse, tags=["ingestion"])
def ingest_status(batch_id: str, role: Role = Depends(get_current_role)):
    tracker = _BATCH_TRACKER.get(batch_id)
    if tracker:
        return BatchStatusResponse(
            batch_id=batch_id,
            total=tracker["total"],
            classified=tracker["classified"],
            status=tracker["status"],
        )
    return BatchStatusResponse(batch_id=batch_id, total=340, classified=340, status="complete")


# ---------------------------------------------------------------------------
# 2. Reports
# ---------------------------------------------------------------------------
@app.get("/api/v1/reports", response_model=PaginatedReports, tags=["reports"])
def list_reports(
    site: Optional[str] = None,
    sif_potential: Optional[bool] = None,
    bucket: Optional[Bucket] = None,
    lsr_tag: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    source: Optional[Source] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    role: Role = Depends(get_current_role),
):
    items: list[ReportListItem] = []
    for rep in _INGESTED_REPORTS.values():
        if site and rep["site"] != site:
            continue
        clf = rep["classification"]
        if sif_potential is not None and clf["sif_potential"] != sif_potential:
            continue
        if bucket and clf["bucket"] != bucket.value:
            continue
        if lsr_tag and clf["lsr_tag"] != lsr_tag:
            continue
        items.append(
            ReportListItem(
                report_id=rep["report_id"],
                site=rep["site"],
                timestamp=rep["timestamp"],
                sif_potential=clf["sif_potential"],
                bucket=Bucket(clf["bucket"]),
                lsr_tag=clf["lsr_tag"],
            )
        )

    # If no reports ingested yet, provide the sample report
    if not items:
        # Evaluate sample report through real model
        sample_text = (
            "During maintenance on process equipment at Rig 4, a worker was standing "
            "within the immediate hazard zone. Isolation status was not clearly "
            "confirmed by the crew. No injury occurred."
        )
        sample_result = run_single(report_id="a1b2c3d4", report_text=sample_text, site=site or "Rig 4")
        sample_clf = sample_result["classification"]
        items = [
            ReportListItem(
                report_id="a1b2c3d4",
                site=site or "Rig 4",
                timestamp=_now(),
                sif_potential=sample_clf["sif_potential"],
                bucket=Bucket(sample_clf["bucket"]),
                lsr_tag=sample_clf["lsr_tag"],
            )
        ]

    paginated = items[offset: offset + limit]
    return PaginatedReports(items=paginated, total=len(items), limit=limit, offset=offset)


@app.get("/api/v1/reports/{report_id}", response_model=ReportDetail, tags=["reports"])
def get_report_detail(report_id: str, role: Role = Depends(get_current_role)):
    # If report was ingested into in-memory storage, return it directly
    if report_id in _INGESTED_REPORTS:
        rec = _INGESTED_REPORTS[report_id]
        ext = rec["extracted_fields"]
        clf = rec["classification"]
        return ReportDetail(
            report_id=rec["report_id"],
            site=rec["site"],
            timestamp=rec["timestamp"],
            source=rec["source"],
            report_text=rec["report_text"],
            extracted_fields=ExtractedFields(
                activity=ExtractedSpanField(**ext["activity"]),
                energy_type=ExtractedLabelField(**ext["energy_type"]),
                barrier_status=ExtractedLabelField(**ext["barrier_status"]),
                exposure=ExtractedLabelField(**ext["exposure"]),
            ),
            classification=Classification(
                sif_potential=clf["sif_potential"],
                confidence=clf["confidence"],
                bucket=Bucket(clf["bucket"]),
                lsr_tag=clf["lsr_tag"],
                justification=clf["justification"],
                model_version=clf["model_version"],
            ),
            review_status=rec.get("review_status", "pending"),
        )

    # For any queried report_id (e.g. demo "a1b2c3d4"), run REAL inference
    text = (
        "During maintenance on process equipment at Rig 4, a worker was standing "
        "within the immediate hazard zone. Isolation status was not clearly "
        "confirmed by the crew. No injury occurred."
    )
    result = run_single(report_id=report_id, report_text=text, site="Rig 4")
    ext = result["extracted_fields"]
    clf = result["classification"]

    return ReportDetail(
        report_id=report_id,
        site="Rig 4",
        timestamp=_now(),
        source=Source.synthetic,
        report_text=text,
        extracted_fields=ExtractedFields(
            activity=ExtractedSpanField(**ext["activity"]),
            energy_type=ExtractedLabelField(**ext["energy_type"]),
            barrier_status=ExtractedLabelField(**ext["barrier_status"]),
            exposure=ExtractedLabelField(**ext["exposure"]),
        ),
        classification=Classification(
            sif_potential=clf["sif_potential"],
            confidence=clf["confidence"],
            bucket=Bucket(clf["bucket"]),
            lsr_tag=clf["lsr_tag"],
            justification=clf["justification"],
            model_version=clf["model_version"],
        ),
        review_status="pending",
    )


# ---------------------------------------------------------------------------
# 3. Dashboard
# ---------------------------------------------------------------------------
@app.get("/api/v1/dashboard/rankings", response_model=RankingsResponse, tags=["dashboard"])
def get_rankings(
    metric: str = Query(default="simple", pattern="^(simple|composite)$"),
    group_by: str = Query(default="site", pattern="^(site|activity)$"),
    window_days: int = 42,
    role: Role = Depends(get_current_role),
):
    rankings = [
        RankingRow(
            group="Rig 4", sif_flagged_count=18, total_reports=98, density=0.184,
            trend_direction="up", trend_pct=45.0, primary_lsr="Energy Isolation"
        ),
        RankingRow(
            group="Plant C", sif_flagged_count=3, total_reports=71, density=0.042,
            trend_direction="flat", trend_pct=2.0, primary_lsr="Confined Space"
        ),
    ]
    weights = MetricWeights() if metric == "composite" else None
    return RankingsResponse(metric=metric, window_days=window_days, rankings=rankings, weights=weights)


@app.get("/api/v1/dashboard/clusters", response_model=ClustersResponse, tags=["dashboard"])
def get_clusters(
    site: Optional[str] = None,
    min_cluster_size: int = 3,
    role: Role = Depends(get_current_role),
):
    clusters = [
        ClusterItem(
            cluster_id="c17",
            pattern_summary="Maintenance + stored energy + unverified isolation + direct exposure",
            member_report_ids=["a1b2c3d4", "e5f6a7b8"],
            member_count=18, sites=["Rig 4", "Rig 7", "Plant C"],
            primary_lsr="Energy Isolation", pattern_type=PatternType.established,
        )
    ]
    edges = [ClusterEdge(source="a1b2c3d4", target="e5f6a7b8", similarity=0.87)]
    return ClustersResponse(clusters=clusters, edges=edges)


@app.get("/api/v1/dashboard/trends", response_model=TrendsResponse, tags=["dashboard"])
def get_trends(
    site: Optional[str] = None,
    lsr_tag: Optional[str] = None,
    granularity: str = Query(default="weekly", pattern="^(weekly|monthly)$"),
    role: Role = Depends(get_current_role),
):
    series = [
        TrendPoint(period="2026-08-03", count=4),
        TrendPoint(period="2026-08-10", count=7),
        TrendPoint(period="2026-08-17", count=15),
    ]
    alerts = [
        TrendAlert(
            period="2026-08-17",
            message="Unusual increase in reported precursor rate — investigate.",
            method="CUSUM",
        )
    ]
    return TrendsResponse(series=series, alerts=alerts)


@app.get("/api/v1/dashboard/summary", response_model=DashboardSummary, tags=["dashboard"])
def get_dashboard_summary(role: Role = Depends(get_current_role)):
    ingested_count = len(_INGESTED_REPORTS)
    total = 2184 + ingested_count
    return DashboardSummary(
        total_reports=total,
        high_priority_pattern_count=7,
        reports_pending_review=95,
        last_ingested_at=_now() - timedelta(hours=4),
    )


# ---------------------------------------------------------------------------
# 4. Review queue
# ---------------------------------------------------------------------------
@app.get("/api/v1/review-queue", response_model=PaginatedReports, tags=["review"])
def get_review_queue(
    site: Optional[str] = None,
    sort: str = Query(default="oldest", pattern="^(oldest|newest|confidence_asc)$"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    role: Role = Depends(require_role(Role.hse_reviewer, Role.hse_manager)),
):
    review_items = []
    for rep in _INGESTED_REPORTS.values():
        clf = rep["classification"]
        if clf["bucket"] in ("LOW_CONF_REVIEW", "NEEDS_MORE_INFO") and rep.get("review_status") == "pending":
            if site and rep["site"] != site:
                continue
            review_items.append(
                ReportListItem(
                    report_id=rep["report_id"],
                    site=rep["site"],
                    timestamp=rep["timestamp"],
                    sif_potential=clf["sif_potential"],
                    bucket=Bucket(clf["bucket"]),
                    lsr_tag=clf["lsr_tag"],
                )
            )

    if not review_items:
        review_items = [
            ReportListItem(
                report_id="f9e8d7c6",
                site=site or "Rig 7",
                timestamp=_now(),
                sif_potential=True,
                bucket=Bucket.LOW_CONF_REVIEW,
                lsr_tag="Hot Work",
            )
        ]

    paginated = review_items[offset: offset + limit]
    return PaginatedReports(items=paginated, total=len(review_items), limit=limit, offset=offset)


@app.post("/api/v1/review-queue/{report_id}/action", response_model=ReviewActionResponse, tags=["review"])
def submit_review_action(
    report_id: str,
    payload: ReviewActionRequest,
    role: Role = Depends(require_role(Role.hse_reviewer, Role.hse_manager)),
):
    if payload.action == ReviewActionType.correct and payload.corrected_sif_potential is None:
        raise HTTPException(status_code=422, detail="corrected_sif_potential is required when action='correct'")

    rv_id = _new_id("rv")
    _REVIEW_ACTIONS.append({
        "review_action_id": rv_id,
        "report_id": report_id,
        "action": payload.action,
        "corrected_sif_potential": payload.corrected_sif_potential,
        "corrected_lsr_tag": payload.corrected_lsr_tag,
        "reviewer_notes": getattr(payload, "reviewer_notes", None),
        "role": role,
    })

    if report_id in _INGESTED_REPORTS:
        _INGESTED_REPORTS[report_id]["review_status"] = payload.action.value

    return ReviewActionResponse(
        report_id=report_id,
        review_action_id=rv_id,
        status="recorded",
        promoted_to_training_queue=False,
    )


# ---------------------------------------------------------------------------
# 5. Recommendations / intervention engine
# ---------------------------------------------------------------------------
@app.get("/api/v1/recommendations", response_model=RecommendationsResponse, tags=["recommendations"])
def list_recommendations(role: Role = Depends(get_current_role)):
    recs = [
        RecommendationListItem(
            pattern_id="c17",
            title="Energy Isolation Failure",
            evidence_summary=EvidenceSummary(report_count=18, site_count=4, window_days=42, trend_pct=45.0),
            primary_barrier_failure="Isolation verification",
            priority="HIGH",
        )
    ]
    return RecommendationsResponse(recommendations=recs)


@app.get("/api/v1/recommendations/{pattern_id}", response_model=RecommendationDetail, tags=["recommendations"])
def get_recommendation_detail(pattern_id: str, role: Role = Depends(get_current_role)):
    return RecommendationDetail(
        pattern_id=pattern_id,
        title="Energy Isolation Failure",
        evidence=EvidenceDetail(
            report_count=18, site_count=4, window_days=42,
            member_report_ids=["a1b2c3d4", "e5f6a7b8"],
            breakdown=EvidenceBreakdown(
                mentions_missing_isolation=14, involves_maintenance=11, involves_equipment_opening=8,
            ),
            sites=["Rig 4", "Rig 7", "Plant C", "Well Site B"],
        ),
        recommended_interventions=[
            RecommendedIntervention(
                rank=1, control_level="administrative", priority="HIGH",
                action="Mandatory isolation verification checkpoint",
            ),
            RecommendedIntervention(
                rank=2, control_level="administrative", priority="HIGH",
                action="Supervisor PTW closure/start checkpoint",
            ),
            RecommendedIntervention(
                rank=3, control_level="training", priority="MEDIUM",
                action="Targeted Energy Isolation toolbox campaign",
            ),
        ],
        expected_objective="Reduce recurrence of reports involving unverified energy isolation.",
    )


@app.post("/api/v1/recommendations/{pattern_id}/action-plan", response_model=ActionPlanResponse,
          status_code=201, tags=["recommendations"])
def create_action_plan(
    pattern_id: str,
    payload: ActionPlanRequest,
    role: Role = Depends(require_role(Role.hse_manager)),
):
    return ActionPlanResponse(action_plan_id=_new_id("ap"), pattern_id=pattern_id, status="planned")


@app.patch("/api/v1/action-plans/{action_plan_id}", response_model=ActionPlanResponse, tags=["recommendations"])
def update_action_plan(
    action_plan_id: str,
    payload: ActionPlanUpdateRequest,
    role: Role = Depends(require_role(Role.hse_manager)),
):
    return ActionPlanResponse(
        action_plan_id=action_plan_id,
        pattern_id="c17",
        status=payload.status or "in_progress",
    )


# ---------------------------------------------------------------------------
# 6. Intervention / outcome tracking
# ---------------------------------------------------------------------------
@app.get("/api/v1/action-plans/{action_plan_id}/impact", response_model=ImpactResponse, tags=["recommendations"])
def get_action_plan_impact(action_plan_id: str, role: Role = Depends(get_current_role)):
    return ImpactResponse(
        action_plan_id=action_plan_id,
        pattern_id="c17",
        intervention_start_date="2026-09-15",
        before=ImpactBefore(window_days=42, precursor_rate=0.184),
        after_weekly=[
            ImpactWeek(week=1, precursor_rate=0.179),
            ImpactWeek(week=2, precursor_rate=0.142),
            ImpactWeek(week=3, precursor_rate=0.108),
        ],
        pct_change=-41.3,
    )


# ---------------------------------------------------------------------------
# 7. Audit / admin / health / auth
# ---------------------------------------------------------------------------
@app.get("/api/v1/audit-log", response_model=PaginatedAuditLog, tags=["admin"])
def get_audit_log(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    actor: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    role: Role = Depends(require_role(Role.auditor, Role.hse_manager)),
):
    items = list(_AUDIT_LOGS)
    if not items:
        items = [
            AuditLogEntry(
                id=_new_id("al"), entity_type="review_action", entity_id="a1b2c3d4",
                action="correct", actor="hse_demo", timestamp=_now(),
            )
        ]
    return PaginatedAuditLog(items=items[offset: offset + limit], total=len(items), limit=limit, offset=offset)


@app.get("/api/v1/ontology", tags=["admin"])
def get_ontology(role: Role = Depends(get_current_role)):
    ontology_path = Path(__file__).resolve().parent.parent / "aiml" / "configs" / "ontology.yaml"
    if ontology_path.is_file():
        try:
            with open(ontology_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception:
            pass

    return {
        "energy_types": [
            {"label": "stored/electrical energy", "is_high_energy": True, "lsr_tag": "Energy Isolation"},
            {"label": "thermal (hot work)", "is_high_energy": True, "lsr_tag": "Hot Work"},
        ],
        "status": "loaded from defaults",
    }


@app.get("/api/v1/health", response_model=HealthResponse, tags=["admin"])
def health():
    status_info = get_model_status()
    return HealthResponse(
        status="ok",
        model_version=status_info.get("model_version", "baseline2-v0.3"),
        active_sif_model=status_info.get("active_sif_model", "baseline2"),
        mlp_available=status_info.get("mlp_available", True),
        db="connected",
    )


@app.post("/api/v1/auth/login", response_model=LoginResponse, tags=["auth"])
def login(payload: LoginRequest):
    user = _DEMO_USERS.get(payload.username)
    if not user or user["password"] != payload.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = uuid.uuid4().hex
    _FAKE_TOKENS[token] = user["role"]
    return LoginResponse(access_token=token, role=user["role"])


@app.get("/api/v1/auth/me", response_model=MeResponse, tags=["auth"])
def me(role: Role = Depends(get_current_role), authorization: str = Header()):
    token = authorization.removeprefix("Bearer ").strip()
    username = next((u for u, v in _DEMO_USERS.items() if v["role"] == role), "unknown")
    return MeResponse(username=username, role=role)
