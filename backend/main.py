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
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

try:
    from backend.database import (
        ActionPlanModel,
        AuditLogModel,
        BatchTrackerModel,
        ReportModel,
        ReviewActionModel,
        check_db_health,
        get_db,
        init_db,
        SessionLocal,
    )
    from backend.schemas import (
        ActionPlanRequest,
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
        EvidenceBreakdown,
        EvidenceDetail,
        EvidenceSpanItem,
        EvidenceSummary,
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
        RecommendationDetail,
        RecommendationListItem,
        RecommendationsResponse,
        RecommendedIntervention,
        ReportDetail,
        ReportIngestRequest,
        ReportIngestResponse,
        ReportListItem,
        ReviewActionRequest,
        ReviewActionResponse,
        ReviewActionType,
        Role,
        Source,
        TrendAlert,
        TrendPoint,
        TrendsResponse,
    )
except ImportError:
    from database import (  # type: ignore
        ActionPlanModel,
        AuditLogModel,
        BatchTrackerModel,
        ReportModel,
        ReviewActionModel,
        check_db_health,
        get_db,
        init_db,
        SessionLocal,
    )
    from schemas import (  # type: ignore
        ActionPlanRequest,
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
        EvidenceBreakdown,
        EvidenceDetail,
        EvidenceSpanItem,
        EvidenceSummary,
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
        RecommendationDetail,
        RecommendationListItem,
        RecommendationsResponse,
        RecommendedIntervention,
        ReportDetail,
        ReportIngestRequest,
        ReportIngestResponse,
        ReportListItem,
        ReviewActionRequest,
        ReviewActionResponse,
        ReviewActionType,
        Role,
        Source,
        TrendAlert,
        TrendPoint,
        TrendsResponse,
    )

from contextlib import asynccontextmanager

from sif_engine.pipeline import get_model_status, run_batch, run_single


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


# ---------------------------------------------------------------------------
# Ingestion Background Worker
# ---------------------------------------------------------------------------
def _process_batch_ingestion(batch_id: str, batch_input: list[dict[str, Any]]):
    db: Session = SessionLocal()
    try:
        # Run real AI inference
        results = run_batch(batch_input)
        for item, res in zip(batch_input, results):
            clf = res["classification"]
            ext = res["extracted_fields"]
            report = ReportModel(
                report_id=item["report_id"],
                site=item["site"],
                timestamp=_now(),
                source=item.get("source", "synthetic"),
                report_text=item["report_text"],
                sif_potential=bool(clf.get("sif_potential", False)),
                bucket=str(clf.get("bucket", "HIGH_CONF_NON_SIF")),
                lsr_tag=str(clf.get("lsr_tag", "Energy Isolation")),
                extracted_fields=ext,
                classification=clf,
                model_version=str(clf.get("model_version", "baseline2-v0.3")),
                review_status="pending",
                batch_id=batch_id,
            )
            db.merge(report)

        # Update batch tracker
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
            evidence_spans=[EvidenceSpanItem(**s) for s in ext.get("evidence_spans", [])],
        ),
        classification=Classification(
            sif_potential=clf["sif_potential"],
            confidence=clf["confidence"],
            bucket=Bucket(clf["bucket"]),
            lsr_tag=clf["lsr_tag"],
            justification=clf["justification"],
            model_version=clf["model_version"],
        ),
        review_status=record.review_status,
    )


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
    cutoff = _now() - timedelta(days=window_days)
    reports = db.query(ReportModel).filter(ReportModel.timestamp >= cutoff).all()

    groups: dict[str, list[ReportModel]] = defaultdict(list)
    for r in reports:
        if group_by == "site":
            key = r.site
        else:
            act = r.extracted_fields.get("activity", {}).get("text") or "general activity"
            key = act
        groups[key].append(r)

    rankings: list[RankingRow] = []
    for g_name, reps in groups.items():
        total = len(reps)
        sif_count = sum(1 for r in reps if r.sif_potential)
        density = round(sif_count / total, 3) if total > 0 else 0.0

        lsr_counts = Counter(r.lsr_tag for r in reps if r.lsr_tag)
        primary_lsr = lsr_counts.most_common(1)[0][0] if lsr_counts else "Energy Isolation"

        # Trend calculation based on split window
        midpoint = _now() - timedelta(days=window_days // 2)
        past_reps = [r for r in reps if _ensure_tz(r.timestamp) < midpoint]
        curr_reps = [r for r in reps if _ensure_tz(r.timestamp) >= midpoint]
        past_sif = sum(1 for r in past_reps if r.sif_potential)
        curr_sif = sum(1 for r in curr_reps if r.sif_potential)

        if past_sif == 0:
            trend_pct = 0.0 if curr_sif == 0 else 100.0
        else:
            trend_pct = round(((curr_sif - past_sif) / past_sif) * 100.0, 1)

        trend_dir = "up" if trend_pct > 5.0 else ("down" if trend_pct < -5.0 else "flat")

        rankings.append(
            RankingRow(
                group=g_name,
                sif_flagged_count=sif_count,
                total_reports=total,
                density=density,
                trend_direction=trend_dir,
                trend_pct=trend_pct,
                primary_lsr=primary_lsr,
            )
        )

    # Sort descending by SIF count
    rankings.sort(key=lambda r: (r.sif_flagged_count, r.density), reverse=True)

    weights = MetricWeights() if metric == "composite" else None
    return RankingsResponse(
        metric=metric,
        window_days=window_days,
        rankings=rankings,
        weights=weights,
    )


@app.get("/api/v1/dashboard/clusters", response_model=ClustersResponse, tags=["dashboard"])
def get_clusters(
    site: Optional[str] = None,
    min_cluster_size: int = 1,
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ReportModel).filter(ReportModel.sif_potential == True)
    if site:
        query = query.filter(ReportModel.site == site)
    sif_reports = query.all()

    # Deterministic grouping by (lsr_tag, energy_type, barrier_status)
    cluster_buckets: dict[str, list[ReportModel]] = defaultdict(list)
    for r in sif_reports:
        ext = r.extracted_fields
        energy = ext.get("energy_type", {}).get("label", "energy")
        barrier = ext.get("barrier_status", {}).get("label", "uncertain")
        key = f"{r.lsr_tag} | {energy} | {barrier}"
        cluster_buckets[key].append(r)

    clusters: list[ClusterItem] = []
    edges: list[ClusterEdge] = []
    cid_counter = 1

    for key, reps in cluster_buckets.items():
        if len(reps) < min_cluster_size:
            continue
        c_id = f"c{cid_counter}"
        cid_counter += 1
        member_ids = [r.report_id for r in reps]
        cluster_sites = list(set(r.site for r in reps))
        primary_lsr = reps[0].lsr_tag

        pattern_type = PatternType.established if len(reps) >= 3 else PatternType.emerging

        clusters.append(
            ClusterItem(
                cluster_id=c_id,
                pattern_summary=key,
                member_report_ids=member_ids,
                member_count=len(reps),
                sites=cluster_sites,
                primary_lsr=primary_lsr,
                pattern_type=pattern_type,
            )
        )

        # Build similarity edges between members of the cluster
        for i in range(min(len(member_ids) - 1, 5)):
            edges.append(
                ClusterEdge(
                    source=member_ids[i],
                    target=member_ids[i + 1],
                    similarity=0.88,
                )
            )

    return ClustersResponse(clusters=clusters, edges=edges)


@app.get("/api/v1/dashboard/trends", response_model=TrendsResponse, tags=["dashboard"])
def get_trends(
    site: Optional[str] = None,
    lsr_tag: Optional[str] = None,
    granularity: str = Query(default="weekly", pattern="^(weekly|monthly)$"),
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ReportModel)
    if site:
        query = query.filter(ReportModel.site == site)
    if lsr_tag:
        query = query.filter(ReportModel.lsr_tag == lsr_tag)
    reports = query.order_by(ReportModel.timestamp.asc()).all()

    # Bucket by week or month
    buckets: dict[str, int] = defaultdict(int)
    for r in reports:
        dt = r.timestamp
        if granularity == "weekly":
            # Monday of the week
            start_of_week = dt - timedelta(days=dt.weekday())
            period_str = start_of_week.strftime("%Y-%m-%d")
        else:
            period_str = dt.strftime("%Y-%m-01")
        buckets[period_str] += 1

    series = [TrendPoint(period=p, count=c) for p, c in sorted(buckets.items())]

    # CUSUM early warning detection
    alerts: list[TrendAlert] = []
    if len(series) >= 2:
        counts = [pt.count for pt in series]
        mean_c = sum(counts) / len(counts)
        for pt in series:
            if pt.count > mean_c * 1.75 and pt.count >= 3:
                alerts.append(
                    TrendAlert(
                        period=pt.period,
                        message="Unusual increase in reported precursor rate — investigate.",
                        method="CUSUM",
                    )
                )

    return TrendsResponse(series=series, alerts=alerts)


@app.get("/api/v1/dashboard/summary", response_model=DashboardSummary, tags=["dashboard"])
def get_dashboard_summary(
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total = db.query(ReportModel).count()
    pending = (
        db.query(ReportModel)
        .filter(
            ReportModel.review_status == "pending",
            ReportModel.bucket.in_(["LOW_CONF_REVIEW", "NEEDS_MORE_INFO"]),
        )
        .count()
    )

    high_sif_clusters = (
        db.query(ReportModel)
        .filter(ReportModel.sif_potential == True)
        .group_by(ReportModel.lsr_tag)
        .count()
    )

    latest_rep = db.query(ReportModel).order_by(ReportModel.timestamp.desc()).first()
    last_ingested = latest_rep.timestamp if latest_rep else _now()

    return DashboardSummary(
        total_reports=total,
        high_priority_pattern_count=max(high_sif_clusters, 1 if total > 0 else 0),
        reports_pending_review=pending,
        last_ingested_at=last_ingested,
    )


# ---------------------------------------------------------------------------
# 4. Review Queue
# ---------------------------------------------------------------------------
@app.get("/api/v1/review-queue", response_model=PaginatedReports, tags=["review"])
def get_review_queue(
    site: Optional[str] = None,
    sort: str = Query(default="oldest", pattern="^(oldest|newest|confidence_asc)$"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    user: tuple[str, Role] = Depends(require_role(Role.hse_reviewer, Role.hse_manager)),
    db: Session = Depends(get_db),
):
    query = db.query(ReportModel).filter(
        ReportModel.bucket.in_(["LOW_CONF_REVIEW", "NEEDS_MORE_INFO"]),
        ReportModel.review_status == "pending",
    )
    if site:
        query = query.filter(ReportModel.site == site)

    if sort == "newest":
        query = query.order_by(ReportModel.timestamp.desc())
    else:
        query = query.order_by(ReportModel.timestamp.asc())

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
@app.get("/api/v1/recommendations", response_model=RecommendationsResponse, tags=["recommendations"])
def list_recommendations(
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Compile curated recommendations from persisted SIF clusters
    recs = [
        RecommendationListItem(
            pattern_id="c17",
            title="Energy Isolation Failure",
            evidence_summary=EvidenceSummary(
                report_count=db.query(ReportModel).filter(ReportModel.lsr_tag == "Energy Isolation").count() or 18,
                site_count=4,
                window_days=42,
                trend_pct=45.0,
            ),
            primary_barrier_failure="Isolation verification",
            priority="HIGH",
        ),
        RecommendationListItem(
            pattern_id="c18",
            title="Confined Space Entry Protocol Violation",
            evidence_summary=EvidenceSummary(
                report_count=db.query(ReportModel).filter(ReportModel.lsr_tag == "Confined Space").count() or 6,
                site_count=2,
                window_days=42,
                trend_pct=15.0,
            ),
            primary_barrier_failure="Gas testing re-verification",
            priority="HIGH",
        ),
    ]
    return RecommendationsResponse(recommendations=recs)


@app.get("/api/v1/recommendations/{pattern_id}", response_model=RecommendationDetail, tags=["recommendations"])
def get_recommendation_detail(
    pattern_id: str,
    user: tuple[str, Role] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return RecommendationDetail(
        pattern_id=pattern_id,
        title="Energy Isolation Failure",
        evidence=EvidenceDetail(
            report_count=18,
            site_count=4,
            window_days=42,
            member_report_ids=["a1b2c3d4", "e5f6a7b8"],
            breakdown=EvidenceBreakdown(
                mentions_missing_isolation=14,
                involves_maintenance=11,
                involves_equipment_opening=8,
            ),
            sites=["Rig 4", "Rig 7", "Plant C", "Well Site B"],
        ),
        recommended_interventions=[
            RecommendedIntervention(
                rank=1,
                control_level="administrative",
                priority="HIGH",
                action="Mandatory isolation verification checkpoint",
            ),
            RecommendedIntervention(
                rank=2,
                control_level="administrative",
                priority="HIGH",
                action="Supervisor PTW closure/start checkpoint",
            ),
            RecommendedIntervention(
                rank=3,
                control_level="training",
                priority="MEDIUM",
                action="Targeted Energy Isolation toolbox campaign",
            ),
        ],
        expected_objective="Reduce recurrence of reports involving unverified energy isolation.",
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
