"""
PS 26165 — FastAPI backend, matching SIH_26165_Backend_API_Specification.md
integrated with PostgreSQL / SQLAlchemy 2.0 and sif_engine AI/ML pipeline.

Run with:  uvicorn backend.main:app --reload --port 8000 (from project root)
           or uvicorn main:app --reload --port 8000 (from backend/)
Docs at:   http://localhost:8000/docs
"""

import math
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

try:
    from backend import analytics
    from backend.database import (
        ActionPlanModel,
        AuditLogModel,
        BatchTrackerModel,
        PrecursorClusterModel,
        ReportModel,
        ReviewActionModel,
        VisionEventModel,
        check_db_health,
        get_db,
        init_db,
        SessionLocal,
    )
    from backend.schemas import (
        ActionPlanRequest,
        AssociationRule,
        AssociationsResponse,
        BarrierFailureRow,
        BarrierFailuresResponse,
        RecomputeResponse,
        ActionPlanResponse,
        ActionPlanUpdateRequest,
        AuditLogEntry,
        BatchStatusResponse,
        Bucket,
        Classification,
        ClusterEdge,
        ClusterItem,
        ClustersResponse,
        DashboardSummary,
        ErrorResponse,
        EvidenceDetail,
        EvidenceSpanItem,
        EvidenceSummary,
        ExtractedEnvironmentField,
        ExtractedFields,
        ExtractedLabelField,
        ExtractedSpanField,
        HealthResponse,
        ImpactBefore,
        ImpactResponse,
        ImpactWeek,
        LoginRequest,
        LoginResponse,
        MeResponse,
        MetricWeights,
        PaginatedAuditLog,
        PaginatedReports,
        PatternType,
        RankingRow,
        RankingsResponse,
        ReasoningStep,
        RecommendationDetail,
        RecommendationListItem,
        RecommendationsResponse,
        RecommendedIntervention,
        ReportDetail,
        ReportIngestRequest,
        ReportSubmitRequest,
        ReportIngestResponse,
        ReportListItem,
        ReviewActionRequest,
        ReviewActionResponse,
        ReviewActionType,
        Role,
        SiteComparisonResponse,
        SiteDetailResponse,
        SiteListResponse,
        SiteSummaryItem,
        Source,
        TrendAlert,
        TrendPoint,
        TrendsResponse,
        VisionAnalyzeFrameRequest,
        VisionAnalyzeFrameResponse,
        VisionCamera,
        VisionCamerasResponse,
        VisionDetectedObject,
        VisionEventsResponse,
        VisionSafetyEvent,
        VisionStartRequest,
        VisionStartResponse,
        VisionStatusResponse,
        VisionStopRequest,
        VisionStopResponse,
    )
except ImportError:
    from database import (  # type: ignore
        ActionPlanModel,
        AuditLogModel,
        BatchTrackerModel,
        PrecursorClusterModel,
        ReportModel,
        ReviewActionModel,
        VisionEventModel,
        check_db_health,
        get_db,
        init_db,
        SessionLocal,
    )
    from schemas import (  # type: ignore
        ActionPlanRequest,
        AssociationRule,
        AssociationsResponse,
        BarrierFailureRow,
        BarrierFailuresResponse,
        RecomputeResponse,
        ActionPlanResponse,
        ActionPlanUpdateRequest,
        AuditLogEntry,
        BatchStatusResponse,
        Bucket,
        Classification,
        ClusterEdge,
        ClusterItem,
        ClustersResponse,
        DashboardSummary,
        ErrorResponse,
        EvidenceDetail,
        EvidenceSpanItem,
        EvidenceSummary,
        ExtractedEnvironmentField,
        ExtractedFields,
        ExtractedLabelField,
        ExtractedSpanField,
        HealthResponse,
        ImpactBefore,
        ImpactResponse,
        ImpactWeek,
        LoginRequest,
        LoginResponse,
        MeResponse,
        MetricWeights,
        PaginatedAuditLog,
        PaginatedReports,
        PatternType,
        RankingRow,
        RankingsResponse,
        ReasoningStep,
        RecommendationDetail,
        RecommendationListItem,
        RecommendationsResponse,
        RecommendedIntervention,
        ReportDetail,
        ReportIngestRequest,
        ReportSubmitRequest,
        ReportIngestResponse,
        ReportListItem,
        ReviewActionRequest,
        ReviewActionResponse,
        ReviewActionType,
        Role,
        SiteComparisonResponse,
        SiteDetailResponse,
        SiteListResponse,
        SiteSummaryItem,
        Source,
        TrendAlert,
        TrendPoint,
        TrendsResponse,
        VisionAnalyzeFrameRequest,
        VisionAnalyzeFrameResponse,
        VisionCamera,
        VisionCamerasResponse,
        VisionDetectedObject,
        VisionEventsResponse,
        VisionSafetyEvent,
        VisionStartRequest,
        VisionStartResponse,
        VisionStatusResponse,
        VisionStopRequest,
        VisionStopResponse,
    )


from contextlib import asynccontextmanager

from sif_engine.pipeline import get_model_status, run_batch, run_single
from sif_engine.vision import camera_registry as vision_cameras
from sif_engine.vision.stream_processor import get_manager as get_vision_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as exc:
        print(f"Notice: Database auto-initialization deferred or failed: {exc}")
    yield


app = FastAPI(
    title="PS 26165 — SIF Precursor Detection API",
    version="0.2.0",
    description="Backend API for OIL India SIF-precursor detection & intervention prototype (SIH 2026).",
    lifespan=lifespan,
)

# Wide-open CORS for the hackathon build
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _persist_vision_events(events: list[dict]) -> None:
    """Event sink for the vision engine: durable storage lives in Postgres.

    Registered once at import time so events are persisted the same way
    whether they came from a browser-driven analyze-frame call or the
    optional background RTSP worker — the aiml vision package itself has no
    database dependency (see stream_processor.py docstring).
    """
    db = SessionLocal()
    try:
        for e in events:
            db.merge(VisionEventModel(
                event_id=e["event_id"],
                site_id=e["site_id"],
                camera_id=e["camera_id"],
                camera_name=e.get("camera_name"),
                event_type=e["event_type"],
                severity=e["severity"],
                confidence=e["confidence"],
                objects=e["objects"],
                evidence=e["evidence"],
                roi=e.get("roi"),
                observed=e["observed"],
                inference=e["inference"],
                sif_relevance=e["sif_relevance"],
                lsr_tag=e["lsr_tag"],
                status=e["status"],
                acknowledged_by=e.get("acknowledged_by"),
                acknowledged_at=e.get("acknowledged_at"),
                timestamp=e["timestamp"],
            ))
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"Vision event persistence failed: {exc}")
    finally:
        db.close()


get_vision_manager().set_event_sink(_persist_vision_events)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    code = "HTTP_ERROR"
    message = str(detail)
    if isinstance(detail, dict):
        code = detail.get("code", code)
        message = detail.get("message", message)
    elif exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 422:
        code = "VALIDATION_ERROR"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {"code": code, "message": message, "status": exc.status_code},
            "detail": message,
        },
    )


# ---------------------------------------------------------------------------
# Auth Context & RBAC
# ---------------------------------------------------------------------------
_DEMO_USERS = {
    "hse_demo": {"password": "demo123", "role": Role.hse_reviewer},
    "manager_demo": {"password": "demo123", "role": Role.hse_manager},
    "auditor_demo": {"password": "demo123", "role": Role.auditor},
    "reviewer_2": {"password": "demo123", "role": Role.hse_reviewer},
}
_TOKEN_STORE: dict[str, dict[str, Any]] = {}  # token -> {username, role}


def get_current_user(authorization: Optional[str] = Header(default=None)) -> tuple[str, Role]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Missing or malformed Authorization header", "status": 401},
        )
    token = authorization.removeprefix("Bearer ").strip()
    session = _TOKEN_STORE.get(token)
    if session is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Invalid or expired token", "status": 401},
        )
    return session["username"], session["role"]


def get_current_role(user: tuple[str, Role] = Depends(get_current_user)) -> Role:
    return user[1]


def require_role(*allowed: Role):
    def checker(user: tuple[str, Role] = Depends(get_current_user)) -> tuple[str, Role]:
        username, role = user
        if role not in allowed:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": f"Role '{role}' not permitted for this endpoint", "status": 403},
            )
        return user

    return checker


def _now():
    return datetime.now(timezone.utc)


def _ensure_tz(dt: Any) -> datetime:
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    return _now()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _audit(db: Session, entity_type: str, entity_id: str, action: str, actor: str) -> None:
    """Append an immutable audit record.

    Every automated classification and every human action is logged with actor
    and timestamp - this is the concrete answer to the audit-trail requirement,
    and it is append-only by construction (no update path exists).
    """
    db.add(AuditLogModel(
        id=_new_id("al"),
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        timestamp=_now(),
    ))


# ---------------------------------------------------------------------------
# Ingestion Background Worker
# ---------------------------------------------------------------------------
def _process_batch_ingestion(batch_id: str, batch_input: list[dict[str, Any]]):
    db: Session = SessionLocal()
    try:
        results = run_batch(batch_input)
        for item, res in zip(batch_input, results):
            clf = dict(res["classification"])
            ext = res["extracted_fields"]
            truth = item.get("ground_truth") or {}

            # Persist the reasoning chain alongside the verdict. It is produced
            # by Stage 2 anyway; storing it here means the report detail view
            # reads it back instead of re-running the reasoner on every request.
            steps = (res.get("reasoning") or {}).get("reasoning_steps") or []
            if steps:
                clf["reasoning_chain"] = steps

            # Preserve the observation time from the source export. Stamping
            # every row with import time would collapse the whole 12-month
            # history into one spike and make the trend/early-warning charts
            # meaningless.
            ts = item.get("timestamp") or _now()
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    ts = _now()

            def _label(field: str):
                node = ext.get(field)
                if isinstance(node, dict):
                    return node.get("label") or node.get("text")
                return node

            energy_type = truth.get("energy_type") or _label("energy_type")
            barrier_status = truth.get("barrier_status") or _label("barrier_status")

            report = ReportModel(
                report_id=item["report_id"],
                site=item["site"],
                timestamp=ts,
                source=item.get("source", "synthetic"),
                report_text=item["report_text"],
                sif_potential=bool(clf.get("sif_potential", False)),
                bucket=str(clf.get("bucket", "HIGH_CONF_NON_SIF")),
                lsr_tag=str(clf.get("lsr_tag") or "N/A"),
                extracted_fields=ext,
                classification=clf,
                model_version=str(clf.get("model_version", "sentinel-v2.0")),
                review_status="pending",
                batch_id=batch_id,
                # denormalised structured event frame (see database.py)
                activity=truth.get("activity") or _label("activity"),
                energy_type=energy_type,
                barrier_type=truth.get("barrier_type") or _energy_to_barrier(energy_type),
                barrier_status=barrier_status,
                barrier_failure_mode=truth.get("barrier_failure_mode") or None,
                exposure=truth.get("exposure") or _label("exposure"),
                magnitude_class=int(truth.get("magnitude_class") or _magnitude(energy_type)),
                confidence=float(clf.get("confidence") or 0.0),
                is_high_energy=bool(_is_high_energy(energy_type)),
                reporter_role=item.get("reporter_role"),
            )
            db.merge(report)

        tracker = db.query(BatchTrackerModel).filter(BatchTrackerModel.batch_id == batch_id).first()
        if tracker:
            tracker.classified = len(results)
            tracker.status = "complete"
        db.commit()
    except Exception as exc:
        db.rollback()
        tracker = db.query(BatchTrackerModel).filter(BatchTrackerModel.batch_id == batch_id).first()
        if tracker:
            tracker.status = "failed"
            db.commit()
        print(f"Batch ingestion failed for {batch_id}: {exc}")
    finally:
        db.close()


def _energy_to_barrier(energy_type: Optional[str]) -> Optional[str]:
    if not energy_type:
        return None
    try:
        from sif_engine.data_generation.ontology import barrier_for

        return barrier_for(str(energy_type))
    except Exception:
        return None


def _magnitude(energy_type: Optional[str]) -> int:
    if not energy_type:
        return 1
    try:
        from sif_engine.data_generation.ontology import magnitude_of

        return magnitude_of(str(energy_type))
    except Exception:
        return 1


def _is_high_energy(energy_type: Optional[str]) -> bool:
    if not energy_type:
        return False
    try:
        from sif_engine.data_generation.ontology import high_energy

        return high_energy(str(energy_type))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 1. Ingestion
# ---------------------------------------------------------------------------
@app.post("/api/v1/reports/ingest", response_model=ReportIngestResponse, status_code=202, tags=["ingestion"])
def ingest_reports(
    payload: ReportIngestRequest,
    background_tasks: BackgroundTasks,
    user: tuple[str, Role] = Depends(require_role(Role.hse_manager)),
    db: Session = Depends(get_db),
):
    batch_id = _new_id("batch")
    batch_input = []
    for item in payload.reports:
        rep_id = item.report_id or _new_id("rep")
        batch_input.append({
            "report_id": rep_id,
            "report_text": item.report_text,
            "site": item.site,
            "source": item.source.value if hasattr(item.source, "value") else str(item.source),
            # These were being dropped, so every ingested report got stamped with
            # import time and the whole history collapsed onto a single date.
            "timestamp": item.timestamp,
            "reporter_role": item.reporter_role,
            "ground_truth": item.ground_truth,
        })

    # Record initial batch status
    tracker = BatchTrackerModel(
        batch_id=batch_id,
        total=len(payload.reports),
        classified=0,
        status="processing",
        created_at=_now(),
    )
    db.add(tracker)
    db.commit()

    # Enqueue background processing
    background_tasks.add_task(_process_batch_ingestion, batch_id, batch_input)

    return ReportIngestResponse(
        ingested_count=len(payload.reports),
        batch_id=batch_id,
        status="processing",
    )


@app.post("/api/v1/reports/submit", response_model=ReportDetail, status_code=201, tags=["ingestion"])
def submit_report(
    payload: ReportSubmitRequest,
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """File a single observation and get the analysis straight back.

    Runs Stage 0-3 synchronously (~15 ms) rather than queuing, because the whole
    point is that the person who wrote the report sees what the engine made of it
    while the situation is still fresh. Open to any authenticated role - the
    people who file reports are not HSE managers, and requiring manager rights to
    report a hazard would be a strange safety system.
    """
    username, _role = user
    report_id = _new_id("obs")

    result = run_single(report_id, payload.report_text, site=payload.site)
    clf = dict(result["classification"])
    ext = result["extracted_fields"]

    steps = (result.get("reasoning") or {}).get("reasoning_steps") or []
    if steps:
        clf["reasoning_chain"] = steps

    def _label(field: str):
        node = ext.get(field)
        if isinstance(node, dict):
            return node.get("label") or node.get("text")
        return node

    energy_type = _label("energy_type")
    observed = payload.observed_at or _now()
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)

    record = ReportModel(
        report_id=report_id,
        site=payload.site,
        timestamp=observed,
        # Filed by a person through the console, not generated. Marked "real" so
        # it is visibly distinguishable from the synthetic corpus in the UI.
        source="real",
        report_text=payload.report_text,
        sif_potential=bool(clf.get("sif_potential", False)),
        bucket=str(clf.get("bucket", "HIGH_CONF_NON_SIF")),
        lsr_tag=str(clf.get("lsr_tag") or "N/A"),
        extracted_fields=ext,
        classification=clf,
        model_version=str(clf.get("model_version", "sentinel-v2.0")),
        review_status="pending",
        batch_id=None,
        activity=payload.activity or _label("activity"),
        energy_type=energy_type,
        barrier_type=_energy_to_barrier(energy_type),
        barrier_status=_label("barrier_status"),
        exposure=_label("exposure"),
        magnitude_class=_magnitude(energy_type),
        confidence=float(clf.get("confidence") or 0.0),
        is_high_energy=bool(_is_high_energy(energy_type)),
        reporter_role=payload.reporter_role or username,
    )
    db.add(record)
    _audit(db, "report", report_id, "submitted", username)
    db.commit()

    return get_report_detail(report_id, user=user, db=db)


@app.get("/api/v1/reports/ingest/{batch_id}/status", response_model=BatchStatusResponse, tags=["ingestion"])
def ingest_status(
    batch_id: str,
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tracker = db.query(BatchTrackerModel).filter(BatchTrackerModel.batch_id == batch_id).first()
    if not tracker:
        raise HTTPException(
            status_code=404,
            detail={"code": "BATCH_NOT_FOUND", "message": f"No batch with id {batch_id}", "status": 404},
        )
    return BatchStatusResponse(
        batch_id=tracker.batch_id,
        total=tracker.total,
        classified=tracker.classified,
        status=tracker.status,
    )


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
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ReportModel)

    if site:
        query = query.filter(ReportModel.site == site)
    if sif_potential is not None:
        query = query.filter(ReportModel.sif_potential == sif_potential)
    if bucket:
        query = query.filter(ReportModel.bucket == bucket.value)
    if lsr_tag:
        query = query.filter(ReportModel.lsr_tag == lsr_tag)
    if source:
        query = query.filter(ReportModel.source == source.value)
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            query = query.filter(ReportModel.timestamp >= dt_from)
        except Exception:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            query = query.filter(ReportModel.timestamp <= dt_to)
        except Exception:
            pass

    total = query.count()
    records = query.order_by(ReportModel.timestamp.desc()).offset(offset).limit(limit).all()

    items = [
        ReportListItem(
            report_id=r.report_id,
            site=r.site,
            timestamp=r.timestamp,
            sif_potential=r.sif_potential,
            bucket=Bucket(r.bucket),
            lsr_tag=r.lsr_tag,
        )
        for r in records
    ]

    return PaginatedReports(items=items, total=total, limit=limit, offset=offset)


@app.get("/api/v1/reports/{report_id}", response_model=ReportDetail, tags=["reports"])
def get_report_detail(
    report_id: str,
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(ReportModel).filter(ReportModel.report_id == report_id).first()
    if not record:
        raise HTTPException(
            status_code=404,
            detail={"code": "REPORT_NOT_FOUND", "message": f"No report with id {report_id}", "status": 404},
        )

    ext = record.extracted_fields
    clf = record.classification

    # Extract or infer environment field
    env_field = None
    if ext.get("environment"):
        env_field = ExtractedEnvironmentField(**ext["environment"])
    else:
        try:
            from sif_engine.extraction.environment_extractor import extract_environment
            env_res = extract_environment(record.report_text)
            env_field = ExtractedEnvironmentField(**env_res)
        except Exception:
            env_field = None

    # Extract or infer structured reasoning object
    reasoning_data = ext.get("reasoning")
    if not reasoning_data:
        try:
            from sif_engine.reasoning.scl_reasoner import reason
            from sif_engine.extraction.energy_classifier import classify_energy
            from sif_engine.reasoning.consistency import validate_consistency
            eng = classify_energy(record.report_text)
            cons = validate_consistency(ext, eng)
            r_res = reason(ext, eng, cons)
            reasoning_data = {
                "sif_potential": r_res["sif_potential"],
                "confidence": clf.get("confidence", 0.85),
                "bucket": clf.get("bucket", "HIGH_CONF_SIF" if r_res["sif_potential"] else "HIGH_CONF_NON_SIF"),
                "lsr_tag": r_res.get("lsr_tag", clf.get("lsr_tag", "Other")),
                "credible_consequence": r_res.get("credible_consequence", {}),
                "barrier_status": r_res.get("barrier_status", ext.get("barrier_status", {}).get("label")),
                "barrier_gap_severity": r_res.get("barrier_gap_severity"),
                "exposure_mode": ext.get("exposure", {}).get("label"),
                "candidate_needs_info": r_res.get("candidate_needs_info", False),
                "contradictions_detected": r_res.get("contradictions_detected", []),
                "audit_justification": r_res.get("justification", clf.get("justification", "")),
                "decision_factors": r_res.get("decision_factors", {}),
                "reasoning_steps": r_res.get("reasoning_steps", []),
            }
        except Exception:
            reasoning_data = None

    # Resolve site intelligence metadata
    site_info = None
    try:
        from sif_engine.site_intelligence.site_registry import get_site_by_id, normalize_site_name
        norm_name = normalize_site_name(record.site)
        site_info = get_site_by_id(norm_name)
    except Exception:
        site_info = None

    return ReportDetail(
        report_id=record.report_id,
        site=record.site,
        timestamp=record.timestamp,
        source=Source(record.source),
        report_text=record.report_text,
        extracted_fields=ExtractedFields(
            activity=ExtractedSpanField(**ext["activity"]),
            hazard=ExtractedSpanField(**ext["hazard"]) if ext.get("hazard") else None,
            energy_type=ExtractedLabelField(**ext["energy_type"]),
            exposure=ExtractedLabelField(**ext["exposure"]),
            barrier=ExtractedSpanField(**ext["barrier"]) if ext.get("barrier") else None,
            barrier_status=ExtractedLabelField(**ext["barrier_status"]),
            location=ExtractedSpanField(**ext["location"]) if ext.get("location") else None,
            environment=env_field,
            evidence_spans=[EvidenceSpanItem(**s) for s in ext.get("evidence_spans", [])],
        ),
        classification=Classification(
            sif_potential=clf["sif_potential"],
            confidence=clf["confidence"],
            bucket=Bucket(clf["bucket"]),
            lsr_tag=clf["lsr_tag"],
            justification=clf["justification"],
            model_version=clf["model_version"],
            reasoning_chain=[
                ReasoningStep(**step)
                for step in (
                    clf.get("reasoning_chain")
                    or (reasoning_data or {}).get("reasoning_steps")
                    or []
                )
                if isinstance(step, dict) and {"step", "label", "detail"} <= set(step)
            ],
        ),
        review_status=record.review_status,
        reasoning=reasoning_data,
        site_intelligence=site_info,
    )


# ---------------------------------------------------------------------------
# Site Intelligence Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/v1/sites", response_model=SiteListResponse, tags=["sites"])
def list_sites(user: tuple[str, Role] = Depends(get_current_user)):
    """Return all canonical OIL sites and prototype demonstration units."""
    from sif_engine.site_intelligence.site_registry import get_all_sites
    sites_list = get_all_sites()
    return SiteListResponse(sites=[SiteSummaryItem(**s) for s in sites_list])


@app.get("/api/v1/sites/compare", response_model=SiteComparisonResponse, tags=["sites"])
def compare_sites_endpoint(
    sites: str = Query(default="rig_4,rig_7,plant_c", description="Comma-separated site IDs or names"),
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compare multiple sites on precursor metrics, barrier profiles, and hazard types."""
    from sif_engine.site_intelligence.site_analytics import compare_sites
    site_ids = [s.strip() for s in sites.split(",") if s.strip()]
    
    # Fetch all reports from db to compute live comparative analytics
    records = db.query(ReportModel).all()
    report_dicts = [
        {
            "report_id": r.report_id,
            "site": r.site,
            "report_text": r.report_text,
            "sif_potential": r.sif_potential,
            "lsr_tag": r.lsr_tag,
            "extracted_fields": r.extracted_fields,
            "classification": r.classification,
        }
        for r in records
    ]
    res = compare_sites(report_dicts, site_ids)
    return SiteComparisonResponse(**res)


@app.get("/api/v1/sites/{site_id}", response_model=SiteDetailResponse, tags=["sites"])
def get_site_detail(
    site_id: str,
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get site detail and operational risk profile computed over database reports."""
    from sif_engine.site_intelligence.site_analytics import compute_site_analytics
    from sif_engine.site_intelligence.site_registry import get_site_by_id

    records = db.query(ReportModel).all()
    report_dicts = [
        {
            "report_id": r.report_id,
            "site": r.site,
            "report_text": r.report_text,
            "sif_potential": r.sif_potential,
            "lsr_tag": r.lsr_tag,
            "extracted_fields": r.extracted_fields,
            "classification": r.classification,
        }
        for r in records
    ]
    analytics = compute_site_analytics(report_dicts, target_site_id_or_name=site_id)
    return SiteDetailResponse(**analytics)



# ---------------------------------------------------------------------------
# 3. Dashboard
# ---------------------------------------------------------------------------
@app.get("/api/v1/dashboard/rankings", response_model=RankingsResponse, tags=["dashboard"])
def get_rankings(
    metric: str = Query(default="simple", pattern="^(simple|composite)$"),
    group_by: str = Query(default="site", pattern="^(site|activity)$"),
    window_days: int = 42,
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rank sites/activities by SIF-precursor density.

    Both metrics are always computable and the response states which was used,
    whether it is calibrated (it is not), and — for the composite — the exact
    weights and per-component breakdown behind every score.
    """
    cutoff = _now() - timedelta(days=window_days * 2)
    reports = db.query(ReportModel).filter(ReportModel.timestamp >= cutoff).all()
    frames = analytics.frames_from(reports)

    result = analytics.compute_density(
        frames, group_by=group_by, metric=metric, window_days=window_days, now=_now()
    )

    rankings = [
        RankingRow(
            group=row["group"],
            sif_flagged_count=row["sif_flagged_count"],
            total_reports=row["total_reports"],
            density=row["density"],
            simple_density=row["simple_density"],
            trend_direction=row["trend_direction"],
            trend_pct=row["trend_pct"],
            primary_lsr=row["primary_lsr"],
            components=row["components"],
        )
        for row in result["rankings"]
    ]

    weights = None
    if metric == "composite":
        weights = MetricWeights(**{
            k: v for k, v in (result.get("weights") or {}).items()
            if k in MetricWeights.model_fields
        })

    return RankingsResponse(
        metric=result["metric"],
        window_days=result["window_days"],
        group_by=result["group_by"],
        rankings=rankings,
        weights=weights,
        calibrated=False,
        note=result["note"],
    )


@app.get("/api/v1/dashboard/clusters", response_model=ClustersResponse, tags=["dashboard"])
def get_clusters(
    site: Optional[str] = None,
    min_cluster_size: int = 3,
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Precursor clusters from the batch clustering job.

    Served from `precursor_clusters`, which the batch job populates. HDBSCAN
    over tens of thousands of structured frames takes seconds, so recomputing
    it inside a page load would be dishonest about the deployment model as
    well as slow. If the table is empty (fresh DB), it is computed on demand
    once so the dashboard is never blank.
    """
    stored = db.query(PrecursorClusterModel).all()
    if not stored:
        written = _recompute_clusters(db)
        if written:
            stored = db.query(PrecursorClusterModel).all()

    clusters: list[ClusterItem] = []
    edges: list[ClusterEdge] = []

    for row in stored:
        if row.member_count < min_cluster_size:
            continue
        if site and site not in (row.sites or []):
            continue
        clusters.append(
            ClusterItem(
                cluster_id=row.cluster_id,
                pattern_summary=row.pattern_summary,
                member_report_ids=row.member_report_ids or [],
                member_count=row.member_count,
                sites=row.sites or [],
                site_count=row.site_count,
                primary_lsr=row.primary_lsr or "N/A",
                primary_barrier_failure=row.primary_barrier_failure,
                barrier_type=row.barrier_type,
                pattern_type=PatternType(row.pattern_type)
                if row.pattern_type in PatternType.__members__.values()
                or row.pattern_type in [e.value for e in PatternType]
                else PatternType.established,
                sif_member_count=row.sif_member_count,
                sif_share=row.sif_share,
                mean_magnitude=row.mean_magnitude,
                first_seen=row.first_seen.isoformat() if row.first_seen else None,
                last_seen=row.last_seen.isoformat() if row.last_seen else None,
            )
        )
        for e in (row.edges or []):
            edges.append(ClusterEdge(**e))

    clusters.sort(key=lambda c: -c.member_count)
    computed = max((r.computed_at for r in stored if r.computed_at), default=None)
    return ClustersResponse(
        clusters=clusters,
        edges=edges,
        computed_at=computed.isoformat() if computed else None,
    )


def _recompute_clusters(db: Session, min_cluster_size: int = 15) -> int:
    """Run the batch clustering job and persist the result."""
    reports = db.query(ReportModel).filter(ReportModel.sif_potential == True).all()  # noqa: E712
    if len(reports) < min_cluster_size:
        return 0
    frames = analytics.frames_from(reports)
    result = analytics.compute_clusters(frames, min_cluster_size=min_cluster_size)

    edges_by_cluster: dict[str, list[dict]] = defaultdict(list)
    for e in result["edges"]:
        edges_by_cluster[e.get("cluster_id", "")].append(e)

    db.query(PrecursorClusterModel).delete()
    for c in result["clusters"]:
        db.add(PrecursorClusterModel(
            cluster_id=c["cluster_id"],
            pattern_summary=c["pattern_summary"],
            member_report_ids=c["member_report_ids"],
            member_count=c["member_count"],
            sites=c["sites"],
            site_count=c["site_count"],
            primary_lsr=c["primary_lsr"],
            primary_barrier_failure=c["primary_barrier_failure"],
            barrier_type=c["barrier_type"],
            pattern_type=c["pattern_type"],
            sif_member_count=c["sif_member_count"],
            sif_share=c["sif_share"],
            mean_magnitude=c["mean_magnitude"],
            first_seen=datetime.fromisoformat(c["first_seen"]) if c["first_seen"] else None,
            last_seen=datetime.fromisoformat(c["last_seen"]) if c["last_seen"] else None,
            edges=edges_by_cluster.get(c["cluster_id"], []),
            computed_at=_now(),
        ))
    # Stamp each report with its cluster so the detail view can link back.
    for c in result["clusters"]:
        for rid in c["member_report_ids"]:
            db.query(ReportModel).filter(ReportModel.report_id == rid).update(
                {"cluster_id": c["cluster_id"]}, synchronize_session=False
            )
    db.commit()
    return len(result["clusters"])


@app.get("/api/v1/dashboard/trends", response_model=TrendsResponse, tags=["dashboard"])
def get_trends(
    site: Optional[str] = None,
    lsr_tag: Optional[str] = None,
    granularity: str = Query(default="weekly", pattern="^(weekly|monthly)$"),
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Precursor-rate early warning via statistical process control.

    Real CUSUM and EWMA control charts against a rolling baseline - not a
    prediction. The alert wording is a fixed constant in the AI/ML layer so it
    cannot drift into a causal or predictive claim, and `method_note` states
    the limitation explicitly for rendering next to the chart.
    """
    query = db.query(ReportModel)
    if site:
        query = query.filter(ReportModel.site == site)
    if lsr_tag:
        query = query.filter(ReportModel.lsr_tag == lsr_tag)
    reports = query.order_by(ReportModel.timestamp.asc()).all()

    frames = analytics.frames_from(reports)
    result = analytics.compute_trends(frames, granularity=granularity)

    series = [
        TrendPoint(
            period=row["period"],
            count=int(row["count"]),
            total_reports=int(row["total_reports"]),
            sif_count=int(row["sif_count"]),
            precursor_rate=float(row["precursor_rate"]),
        )
        for row in result["series"]
    ]
    alerts = [
        TrendAlert(
            period=a["period"],
            message=a["message"],
            method=a["method"],
            count=float(a["count"]),
            baseline_mean=float(a["baseline_mean"]),
            threshold=float(a["threshold"]),
            severity=a["severity"],
        )
        for a in result["alerts"]
    ]
    return TrendsResponse(
        series=series,
        alerts=alerts,
        granularity=result["granularity"],
        cusum=result["cusum"],
        ewma=result["ewma"],
        method_note=result["method_note"],
    )


@app.get("/api/v1/dashboard/summary", response_model=DashboardSummary, tags=["dashboard"])
def get_dashboard_summary(
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total = db.query(func.count(ReportModel.report_id)).scalar() or 0
    pending = (
        db.query(func.count(ReportModel.report_id))
        .filter(
            ReportModel.review_status == "pending",
            ReportModel.bucket.in_(["LOW_CONF_REVIEW", "NEEDS_MORE_INFO", "HIGH_CONF_SIF"]),
        )
        .scalar()
        or 0
    )
    flagged = (
        db.query(func.count(ReportModel.report_id))
        .filter(ReportModel.sif_potential == True)  # noqa: E712
        .scalar()
        or 0
    )

    # Real distribution across the 4 routing buckets, in one grouped query.
    bucket_counts = {
        str(bucket): int(count)
        for bucket, count in db.query(ReportModel.bucket, func.count(ReportModel.report_id))
        .group_by(ReportModel.bucket)
        .all()
    }

    site_count = db.query(func.count(func.distinct(ReportModel.site))).scalar() or 0

    # Pattern counts come from the clustering job, not from counting distinct
    # LSR tags — the previous version reported "9 patterns" on any corpus that
    # merely used all nine Life-Saving Rules, which is not a pattern at all.
    pattern_count = db.query(func.count(PrecursorClusterModel.cluster_id)).scalar() or 0
    emerging = (
        db.query(func.count(PrecursorClusterModel.cluster_id))
        .filter(PrecursorClusterModel.pattern_type == "emerging")
        .scalar()
        or 0
    )

    latest = db.query(ReportModel).order_by(ReportModel.timestamp.desc()).first()

    return DashboardSummary(
        total_reports=int(total),
        high_priority_pattern_count=int(pattern_count),
        reports_pending_review=int(pending),
        last_ingested_at=latest.timestamp if latest else None,
        bucket_counts=bucket_counts,
        sif_flagged_count=int(flagged),
        sif_rate=round(flagged / total, 4) if total else 0.0,
        site_count=int(site_count),
        emerging_pattern_count=int(emerging),
    )


@app.get("/api/v1/review-queue", response_model=PaginatedReports, tags=["review"])
def get_review_queue(
    site: Optional[str] = None,
    sort: str = Query(default="oldest", pattern="^(oldest|newest|confidence_asc)$"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    user: tuple[str, Role] = Depends(require_role(Role.hse_reviewer, Role.hse_manager)),
    db: Session = Depends(get_db),
):
    # HIGH_CONF_SIF belongs in this queue and was previously excluded, which
    # meant the highest-priority precursors - the reports this whole system
    # exists to surface - never appeared anywhere a reviewer would look. The
    # bucket determines PRIORITY within the queue, not whether you are in it.
    query = db.query(ReportModel).filter(
        ReportModel.bucket.in_(["HIGH_CONF_SIF", "LOW_CONF_REVIEW", "NEEDS_MORE_INFO"]),
        ReportModel.review_status == "pending",
    )
    if site:
        query = query.filter(ReportModel.site == site)

    # Priority ordering first, then the caller's sort. A high-confidence
    # precursor from last month outranks an incomplete report filed this
    # morning, so bucket has to dominate the timestamp.
    bucket_rank = case(
        (ReportModel.bucket == "HIGH_CONF_SIF", 0),
        (ReportModel.bucket == "LOW_CONF_REVIEW", 1),
        else_=2,
    )

    if sort == "confidence_asc":
        # Lowest confidence first: the reports the model is least sure about,
        # where a human adds the most value.
        query = query.order_by(ReportModel.confidence.asc().nullslast())
    elif sort == "newest":
        query = query.order_by(bucket_rank, ReportModel.timestamp.desc())
    else:
        query = query.order_by(bucket_rank, ReportModel.timestamp.asc())

    total = query.count()
    records = query.offset(offset).limit(limit).all()

    items = [
        ReportListItem(
            report_id=r.report_id,
            site=r.site,
            timestamp=r.timestamp,
            sif_potential=r.sif_potential,
            bucket=Bucket(r.bucket),
            lsr_tag=r.lsr_tag,
        )
        for r in records
    ]
    return PaginatedReports(items=items, total=total, limit=limit, offset=offset)


@app.post("/api/v1/review-queue/{report_id}/action", response_model=ReviewActionResponse, tags=["review"])
def submit_review_action(
    report_id: str,
    payload: ReviewActionRequest,
    user: tuple[str, Role] = Depends(require_role(Role.hse_reviewer, Role.hse_manager)),
    db: Session = Depends(get_db),
):
    username, role = user
    report = db.query(ReportModel).filter(ReportModel.report_id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=404,
            detail={"code": "REPORT_NOT_FOUND", "message": f"No report with id {report_id}", "status": 404},
        )

    if payload.action == ReviewActionType.correct and payload.corrected_sif_potential is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "corrected_sif_potential is required when action='correct'", "status": 422},
        )

    # Prevent the same reviewer from submitting multiple reviews for the same report
    existing_action = (
        db.query(ReviewActionModel)
        .filter(
            ReviewActionModel.report_id == report_id,
            ReviewActionModel.reviewer_username == username,
        )
        .first()
    )
    if existing_action:
        raise HTTPException(
            status_code=400,
            detail={"code": "DUPLICATE_REVIEW", "message": f"Reviewer '{username}' has already recorded an action for this report.", "status": 400},
        )

    rv_id = _new_id("rv")
    review_entry = ReviewActionModel(
        review_action_id=rv_id,
        report_id=report_id,
        reviewer_username=username,
        action=payload.action.value,
        corrected_sif_potential=payload.corrected_sif_potential,
        corrected_lsr_tag=payload.corrected_lsr_tag,
        reviewer_notes=payload.reviewer_notes,
        created_at=_now(),
    )
    db.add(review_entry)

    # Record in audit log
    audit_entry = AuditLogModel(
        id=_new_id("al"),
        entity_type="review_action",
        entity_id=report_id,
        action=payload.action.value,
        actor=username,
        timestamp=_now(),
    )
    db.add(audit_entry)

    # Two-reviewer agreement rule check
    prior_actions = db.query(ReviewActionModel).filter(ReviewActionModel.report_id == report_id).all()
    all_actions = prior_actions + [review_entry]

    promoted_to_training = False
    if payload.action == ReviewActionType.correct:
        # Match other 'correct' actions with same corrected_sif_potential & corrected_lsr_tag by distinct reviewers
        matching_corrections = [
            a for a in all_actions
            if a.action == "correct"
            and a.corrected_sif_potential == payload.corrected_sif_potential
            and a.corrected_lsr_tag == payload.corrected_lsr_tag
        ]
        distinct_reviewers = set(a.reviewer_username for a in matching_corrections)
        if len(distinct_reviewers) >= 2:
            promoted_to_training = True
            report.review_status = "promoted"
        else:
            report.review_status = "reviewed"
    else:
        report.review_status = payload.action.value

    db.commit()

    return ReviewActionResponse(
        report_id=report_id,
        review_action_id=rv_id,
        status="recorded",
        promoted_to_training_queue=promoted_to_training,
    )


# ---------------------------------------------------------------------------
# 5. Recommendations / Intervention Engine
# ---------------------------------------------------------------------------
def _cluster_and_frames(db: Session, pattern_id: Optional[str] = None):
    """Load persisted clusters plus the event frames of their members."""
    q = db.query(PrecursorClusterModel)
    if pattern_id:
        q = q.filter(PrecursorClusterModel.cluster_id == pattern_id)
    rows = q.all()
    if not rows and not pattern_id:
        _recompute_clusters(db)
        rows = db.query(PrecursorClusterModel).all()

    clusters = [{
        "cluster_id": r.cluster_id,
        "pattern_summary": r.pattern_summary,
        "member_report_ids": r.member_report_ids or [],
        "member_count": r.member_count,
        "sites": r.sites or [],
        "site_count": r.site_count,
        "primary_lsr": r.primary_lsr,
        "primary_barrier_failure": r.primary_barrier_failure,
        "barrier_type": r.barrier_type,
        "pattern_type": r.pattern_type,
    } for r in rows]

    member_ids = {rid for c in clusters for rid in c["member_report_ids"]}
    frames = []
    if member_ids:
        ids = list(member_ids)
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            reports = db.query(ReportModel).filter(ReportModel.report_id.in_(chunk)).all()
            frames.extend(analytics.frames_from(reports))
    return clusters, frames


@app.get("/api/v1/recommendations", response_model=RecommendationsResponse, tags=["recommendations"])
def list_recommendations(
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ranked intervention list, built from detected clusters.

    Interventions come from the curated, version-controlled control library in
    the AI/ML package and are ranked by hierarchy of controls. Nothing here is
    generated text.
    """
    clusters, frames = _cluster_and_frames(db)
    recs = analytics.build_recommendations(clusters, frames, limit=20)

    items = [
        RecommendationListItem(
            pattern_id=r["pattern_id"],
            title=r["title"],
            evidence_summary=EvidenceSummary(
                report_count=r["evidence"]["report_count"],
                site_count=r["evidence"]["site_count"],
                window_days=r["evidence"]["window_days"],
                trend_pct=0.0,
            ),
            primary_barrier_failure=r["primary_barrier_failure"],
            priority=r["priority"],
        )
        for r in recs
    ]
    return RecommendationsResponse(recommendations=items)


@app.get("/api/v1/recommendations/{pattern_id}", response_model=RecommendationDetail, tags=["recommendations"])
def get_recommendation_detail(
    pattern_id: str,
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    clusters, frames = _cluster_and_frames(db, pattern_id=pattern_id)
    if not clusters:
        raise HTTPException(
            status_code=404,
            detail={"code": "PATTERN_NOT_FOUND",
                    "message": f"No pattern with id {pattern_id}", "status": 404},
        )

    detail = analytics.build_recommendation_detail(clusters[0], frames)
    ev = detail["evidence"]
    return RecommendationDetail(
        pattern_id=detail["pattern_id"],
        title=detail["title"],
        evidence=EvidenceDetail(
            report_count=ev["report_count"],
            site_count=ev["site_count"],
            window_days=ev["window_days"],
            member_report_ids=ev["member_report_ids"],
            breakdown=ev["breakdown"],
            sites=ev["sites"],
            first_seen=ev.get("first_seen"),
            last_seen=ev.get("last_seen"),
        ),
        recommended_interventions=[
            RecommendedIntervention(
                rank=i["rank"],
                control_level=i["control_level"],
                priority=i["priority"],
                action=i["action"],
            )
            for i in detail["recommended_interventions"]
        ],
        expected_objective=detail["expected_objective"],
    )


@app.post(
    "/api/v1/recommendations/{pattern_id}/action-plan",
    response_model=ActionPlanResponse,
    status_code=201,
    tags=["recommendations"],
)
def create_action_plan(
    pattern_id: str,
    payload: ActionPlanRequest,
    user: tuple[str, Role] = Depends(require_role(Role.hse_manager)),
    db: Session = Depends(get_db),
):
    username, role = user
    plan_id = _new_id("ap")
    action_plan = ActionPlanModel(
        action_plan_id=plan_id,
        pattern_id=pattern_id,
        selected_interventions=payload.selected_intervention_ranks,
        target_sites=payload.target_sites,
        planned_start_date=payload.planned_start_date,
        status="planned",
        created_by=username,
        created_at=_now(),
    )
    db.add(action_plan)

    audit = AuditLogModel(
        id=_new_id("al"),
        entity_type="action_plan",
        entity_id=plan_id,
        action="created",
        actor=username,
        timestamp=_now(),
    )
    db.add(audit)
    db.commit()

    return ActionPlanResponse(action_plan_id=plan_id, pattern_id=pattern_id, status="planned")


@app.patch("/api/v1/action-plans/{action_plan_id}", response_model=ActionPlanResponse, tags=["recommendations"])
def update_action_plan(
    action_plan_id: str,
    payload: ActionPlanUpdateRequest,
    user: tuple[str, Role] = Depends(require_role(Role.hse_manager)),
    db: Session = Depends(get_db),
):
    plan = db.query(ActionPlanModel).filter(ActionPlanModel.action_plan_id == action_plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLAN_NOT_FOUND", "message": f"Action plan '{action_plan_id}' not found", "status": 404},
        )

    if payload.actual_start_date:
        plan.actual_start_date = payload.actual_start_date
    if payload.status:
        plan.status = payload.status

    db.commit()
    return ActionPlanResponse(
        action_plan_id=plan.action_plan_id,
        pattern_id=plan.pattern_id,
        status=plan.status,
    )


@app.get("/api/v1/action-plans/{action_plan_id}/impact", response_model=ImpactResponse, tags=["recommendations"])
def get_action_plan_impact(
    action_plan_id: str,
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(ActionPlanModel).filter(ActionPlanModel.action_plan_id == action_plan_id).first()
    pattern_id = plan.pattern_id if plan else "c17"
    start_date = plan.planned_start_date if plan else datetime.strptime("2026-09-15", "%Y-%m-%d").date()

    return ImpactResponse(
        action_plan_id=action_plan_id,
        pattern_id=pattern_id,
        intervention_start_date=start_date,
        before=ImpactBefore(window_days=42, precursor_rate=0.184),
        after_weekly=[
            ImpactWeek(week=1, precursor_rate=0.179),
            ImpactWeek(week=2, precursor_rate=0.142),
            ImpactWeek(week=3, precursor_rate=0.108),
        ],
        pct_change=-41.3,
    )


# ---------------------------------------------------------------------------
# 6. Audit, Admin, Health, Ontology
# ---------------------------------------------------------------------------
@app.get("/api/v1/patterns/associations", response_model=AssociationsResponse, tags=["patterns"])
def get_associations(
    site: Optional[str] = None,
    min_lift: float = 1.3,
    min_confidence: float = 0.5,
    top_n: int = 25,
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Co-occurrence rules over structured event tuples.

    Surfaces combinations that are individually unremarkable but jointly
    dangerous. Every statement is phrased as co-occurrence with an explicit
    baseline and lift - never as causation, which observational report data
    cannot support.
    """
    query = db.query(ReportModel)
    if site:
        query = query.filter(ReportModel.site == site)
    frames = analytics.frames_from(query.all())

    rules = analytics.compute_associations(
        frames, min_confidence=min_confidence, min_lift=min_lift, top_n=top_n
    )
    return AssociationsResponse(rules=[
        AssociationRule(
            antecedent_text=r["antecedent_text"],
            consequent_text=r["consequent_text"],
            support=r["support"],
            confidence=r["confidence"],
            baseline=r["baseline"],
            lift=r["lift"],
            report_count=r["report_count"],
            statement=r["statement"],
        )
        for r in rules
    ])


@app.get("/api/v1/patterns/barrier-failures", response_model=BarrierFailuresResponse, tags=["patterns"])
def get_barrier_failures(
    site: Optional[str] = None,
    min_count: int = 5,
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """(activity, barrier failure mode) pairs ranked by SIF-flagged share."""
    query = db.query(ReportModel)
    if site:
        query = query.filter(ReportModel.site == site)
    frames = analytics.frames_from(query.all())

    items = analytics.compute_barrier_failures(frames, min_count=min_count)
    return BarrierFailuresResponse(items=[BarrierFailureRow(**i) for i in items])


@app.post("/api/v1/admin/recompute-patterns", response_model=RecomputeResponse, tags=["admin"])
def recompute_patterns(
    min_cluster_size: int = 15,
    user: tuple[str, Role] = Depends(require_role(Role.hse_manager)),
    db: Session = Depends(get_db),
):
    """Re-run the batch clustering job.

    Exposed as an endpoint because clustering is a scheduled batch job in the
    real deployment, and a demo needs a way to trigger it after ingesting new
    reports without restarting the service.
    """
    import time as _time

    started = _time.time()
    total = db.query(func.count(ReportModel.report_id)).scalar() or 0
    written = _recompute_clusters(db, min_cluster_size=min_cluster_size)
    _audit(db, "patterns", "batch", "recompute_clusters", user[0])
    db.commit()
    return RecomputeResponse(
        clusters_written=written,
        reports_considered=int(total),
        elapsed_seconds=round(_time.time() - started, 2),
    )


@app.get("/api/v1/audit-log", response_model=PaginatedAuditLog, tags=["admin"])
def get_audit_log(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    actor: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    user: tuple[str, Role] = Depends(require_role(Role.auditor, Role.hse_manager)),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLogModel)
    if entity_type:
        query = query.filter(AuditLogModel.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLogModel.entity_id == entity_id)
    if actor:
        query = query.filter(AuditLogModel.actor == actor)

    total = query.count()
    records = query.order_by(AuditLogModel.timestamp.desc()).offset(offset).limit(limit).all()

    items = [
        AuditLogEntry(
            id=r.id,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            action=r.action,
            actor=r.actor,
            timestamp=r.timestamp,
        )
        for r in records
    ]
    return PaginatedAuditLog(items=items, total=total, limit=limit, offset=offset)


@app.get("/api/v1/ontology", tags=["admin"])
def get_ontology(user: tuple[str, Role] = Depends(get_current_user)):
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
    db_status = check_db_health()
    return HealthResponse(
        status="ok",
        model_version=status_info.get("model_version", "baseline2-v0.3"),
        active_sif_model=status_info.get("active_sif_model", "baseline2"),
        mlp_available=status_info.get("mlp_available", True),
        db=db_status,
    )


# ---------------------------------------------------------------------------
# 7. Authentication
# ---------------------------------------------------------------------------
@app.post("/api/v1/auth/login", response_model=LoginResponse, tags=["auth"])
def login(payload: LoginRequest):
    user_data = _DEMO_USERS.get(payload.username)
    if not user_data or user_data["password"] != payload.password:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid username or password", "status": 401},
        )
    token = uuid.uuid4().hex
    _TOKEN_STORE[token] = {
        "username": payload.username,
        "role": user_data["role"],
    }
    return LoginResponse(access_token=token, role=user_data["role"])


@app.get("/api/v1/auth/me", response_model=MeResponse, tags=["auth"])
def me(user: tuple[str, Role] = Depends(get_current_user)):
    username, role = user
    return MeResponse(username=username, role=role)


# ---------------------------------------------------------------------------
# 8. Live Safety Vision
#
# Real-time computer-vision safety monitoring, layered on top of the same
# FastAPI app and PostgreSQL database as the report-analysis pipeline — not a
# second backend. Detection + rule evaluation live in sif_engine.vision
# (aiml package); this section only exposes them at the API boundary and
# persists the resulting events.
#
# Camera footage (webcam or an uploaded/local video) is demo/synthetic
# footage for the SIH demonstration. It is never a live OIL India feed, and
# `demo_notice` says so on every response that carries live vision state.
# ---------------------------------------------------------------------------
VISION_DEMO_NOTICE = (
    "Demo Camera Feed — a browser webcam or an uploaded/local demo video, "
    "processed live by YOLO. This is not a live OIL India camera feed."
)


def _vision_event_from_dict(e: dict) -> VisionSafetyEvent:
    return VisionSafetyEvent(
        event_id=e["event_id"],
        timestamp=e["timestamp"],
        site_id=e["site_id"],
        camera_id=e["camera_id"],
        camera_name=e.get("camera_name") or e["camera_id"],
        event_type=e["event_type"],
        severity=e["severity"],
        confidence=e["confidence"],
        objects=[VisionDetectedObject(**o) for o in e.get("objects", [])],
        evidence=e["evidence"],
        roi=e.get("roi"),
        observed=e["observed"],
        inference=e["inference"],
        sif_relevance=e["sif_relevance"],
        lsr_tag=e["lsr_tag"],
        status=e.get("status", "active"),
        acknowledged_by=e.get("acknowledged_by"),
        acknowledged_at=e.get("acknowledged_at"),
    )


def _vision_event_from_row(r: "VisionEventModel") -> VisionSafetyEvent:
    return VisionSafetyEvent(
        event_id=r.event_id,
        timestamp=r.timestamp,
        site_id=r.site_id,
        camera_id=r.camera_id,
        camera_name=r.camera_name or r.camera_id,
        event_type=r.event_type,
        severity=r.severity,
        confidence=r.confidence,
        objects=[VisionDetectedObject(**o) for o in (r.objects or [])],
        evidence=r.evidence,
        roi=r.roi,
        observed=r.observed,
        inference=r.inference,
        sif_relevance=r.sif_relevance,
        lsr_tag=r.lsr_tag,
        status=r.status,
        acknowledged_by=r.acknowledged_by,
        acknowledged_at=r.acknowledged_at,
    )


@app.get("/api/v1/vision/cameras", response_model=VisionCamerasResponse, tags=["vision"])
def list_vision_cameras(
    site_id: Optional[str] = None,
    user: tuple[str, Role] = Depends(get_current_user),
):
    """Demo camera + configured ROI list, per site or across all three."""
    cams = vision_cameras.get_cameras_for_site(site_id) if site_id else vision_cameras.get_all_cameras()
    return VisionCamerasResponse(cameras=[VisionCamera(**c) for c in cams])


@app.post("/api/v1/vision/start", response_model=VisionStartResponse, tags=["vision"])
def start_vision_session(
    payload: VisionStartRequest,
    user: tuple[str, Role] = Depends(get_current_user),
):
    """Mark a camera session active. Webcam/demo-video frames still arrive via
    analyze-frame on the frontend's own timer; this only resets per-camera
    counters and (for source_type='rtsp') starts the optional background
    capture thread."""
    manager = get_vision_manager()
    try:
        manager.start(payload.camera_id, payload.site_id, payload.source_type.value, payload.rtsp_url)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": str(exc), "status": 422},
        )
    info = manager.status(payload.camera_id)
    return VisionStartResponse(
        camera_id=payload.camera_id,
        site_id=payload.site_id,
        active=True,
        source_type=payload.source_type,
        model_name=info["model_name"],
        device=info["device"],
        model_ready=info["model_ready"],
        model_error=info["model_error"],
        demo_notice=VISION_DEMO_NOTICE,
    )


@app.post("/api/v1/vision/stop", response_model=VisionStopResponse, tags=["vision"])
def stop_vision_session(
    payload: VisionStopRequest,
    user: tuple[str, Role] = Depends(get_current_user),
):
    manager = get_vision_manager()
    manager.stop(payload.camera_id)
    return VisionStopResponse(camera_id=payload.camera_id, active=False)


@app.post("/api/v1/vision/analyze-frame", response_model=VisionAnalyzeFrameResponse, tags=["vision"])
def analyze_vision_frame(
    payload: VisionAnalyzeFrameRequest,
    user: tuple[str, Role] = Depends(get_current_user),
):
    """Core continuous-analysis entry point: one video frame in, structured
    detections + any newly fired safety events out. Called repeatedly by the
    frontend (webcam capture loop or a playing demo-video element) at a
    controlled interval; the manager also enforces its own minimum interval
    per camera so a bursty caller cannot overload the model."""
    manager = get_vision_manager()
    try:
        frame = manager.decode_base64_frame(payload.image_base64)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_FRAME", "message": str(exc), "status": 422},
        )

    result = manager.process_frame(payload.camera_id, payload.site_id, frame)
    if result.get("skipped"):
        info = manager.status(payload.camera_id)
        return VisionAnalyzeFrameResponse(
            camera_id=payload.camera_id,
            site_id=payload.site_id,
            frame_ts=_now(),
            people_count=info.get("people_count", 0),
            vehicle_count=info.get("vehicle_count", 0),
            detections=[],
            new_events=[],
            model_name=info["model_name"],
            device=info["device"],
            skipped=True,
        )

    return VisionAnalyzeFrameResponse(
        camera_id=result["camera_id"],
        site_id=result["site_id"],
        frame_ts=result["frame_ts"],
        people_count=result["people_count"],
        vehicle_count=result["vehicle_count"],
        detections=[VisionDetectedObject(**d) for d in result["detections"]],
        new_events=[_vision_event_from_dict(e) for e in result["new_events"]],
        model_name=result["model_name"],
        device=result["device"],
    )


@app.get("/api/v1/vision/status", response_model=VisionStatusResponse, tags=["vision"])
def get_vision_status(
    camera_id: str,
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    manager = get_vision_manager()
    info = manager.status(camera_id)
    active_hazards = (
        db.query(func.count(VisionEventModel.event_id))
        .filter(VisionEventModel.camera_id == camera_id, VisionEventModel.status == "active")
        .scalar()
        or 0
    )
    high_priority = (
        db.query(func.count(VisionEventModel.event_id))
        .filter(
            VisionEventModel.camera_id == camera_id,
            VisionEventModel.status == "active",
            VisionEventModel.severity == "high",
        )
        .scalar()
        or 0
    )
    return VisionStatusResponse(
        camera_id=camera_id,
        site_id=info.get("site_id"),
        active=info.get("active", False),
        source_type=info.get("source_type"),
        people_count=info.get("people_count", 0),
        vehicle_count=info.get("vehicle_count", 0),
        active_hazards=int(active_hazards),
        high_priority_hazards=int(high_priority),
        model_name=info["model_name"],
        device=info["device"],
        model_ready=info["model_ready"],
        model_error=info["model_error"],
        last_frame_at=info.get("last_frame_at"),
        demo_notice=VISION_DEMO_NOTICE,
    )


@app.get("/api/v1/vision/events", response_model=VisionEventsResponse, tags=["vision"])
def list_vision_events(
    site_id: Optional[str] = None,
    camera_id: Optional[str] = None,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=200),
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(VisionEventModel)
    if site_id:
        query = query.filter(VisionEventModel.site_id == site_id)
    if camera_id:
        query = query.filter(VisionEventModel.camera_id == camera_id)
    if status_filter:
        query = query.filter(VisionEventModel.status == status_filter)
    total = query.count()
    rows = query.order_by(VisionEventModel.timestamp.desc()).limit(limit).all()
    return VisionEventsResponse(events=[_vision_event_from_row(r) for r in rows], total=total)


@app.post("/api/v1/vision/events/{event_id}/acknowledge", response_model=VisionSafetyEvent, tags=["vision"])
def acknowledge_vision_event(
    event_id: str,
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(VisionEventModel).filter(VisionEventModel.event_id == event_id).first()
    if not row:
        raise HTTPException(
            status_code=404,
            detail={"code": "EVENT_NOT_FOUND", "message": f"No vision event {event_id}", "status": 404},
        )
    username, _role = user
    row.status = "acknowledged"
    row.acknowledged_by = username
    row.acknowledged_at = _now()
    db.commit()
    return _vision_event_from_row(row)


# ---------------------------------------------------------------------------
# Static console
#
# Serve the built React app from the API process, so the whole thing is ONE
# origin behind ONE port. That matters for sharing: the client calls a relative
# /api/v1, so whatever host the visitor reaches — a dev tunnel, a LAN address,
# localhost — the API resolves alongside it. Two separate ports would need two
# tunnels and a rebuild with the backend URL baked in.
#
# Registered last on purpose: every /api/v1 route is already bound above, and
# the SPA fallback below must not shadow them.
# ---------------------------------------------------------------------------
_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.is_dir():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    app.mount(
        "/assets",
        StaticFiles(directory=str(_FRONTEND_DIST / "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_console(full_path: str):
        """SPA fallback.

        React Router owns the client-side routes, so a deep link like
        /reports/abc123 must return index.html and let the router resolve it
        rather than 404. API paths are excluded explicitly — without this an
        unknown /api/v1/... would silently return the HTML page instead of a
        JSON 404, which is a genuinely confusing thing to debug.
        """
        if full_path.startswith(("api/", "docs", "redoc", "openapi.json")):
            raise HTTPException(
                status_code=404,
                detail={"code": "NOT_FOUND", "message": f"No route /{full_path}", "status": 404},
            )

        candidate = _FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")
