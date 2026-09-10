"""
PS 26165 — Pydantic schemas for the backend API.
These match SIH_26165_Backend_API_Specification.md exactly, field-for-field.
Import these into main.py's route handlers as request/response_model types.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Bucket(str, Enum):
    HIGH_CONF_SIF = "HIGH_CONF_SIF"
    LOW_CONF_REVIEW = "LOW_CONF_REVIEW"
    HIGH_CONF_NON_SIF = "HIGH_CONF_NON_SIF"
    NEEDS_MORE_INFO = "NEEDS_MORE_INFO"


class Source(str, Enum):
    synthetic = "synthetic"
    real = "real"


class Role(str, Enum):
    hse_reviewer = "hse_reviewer"
    hse_manager = "hse_manager"
    auditor = "auditor"


class ReviewActionType(str, Enum):
    confirm = "confirm"
    correct = "correct"
    reject = "reject"


class PatternType(str, Enum):
    established = "established"
    emerging = "emerging"
    sporadic_high_severity = "sporadic_high_severity"


# ---------------------------------------------------------------------------
# Error envelope
# ---------------------------------------------------------------------------
class ErrorDetail(BaseModel):
    code: str
    message: str
    status: int


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
class ReportIngestItem(BaseModel):
    report_id: Optional[str] = None
    site: str
    report_text: str
    source: Source = Source.synthetic
    # The observation time from the source export. Without it every ingested
    # report would be stamped "now", which silently destroys the trend and
    # early-warning charts - they would all show a single spike at import time.
    timestamp: Optional[datetime] = None
    reporter_role: Optional[str] = None
    # Ground-truth columns, present only for the labelled synthetic corpus.
    # Retained so evaluation views can compare prediction against label; never
    # used by the pipeline to make a prediction.
    ground_truth: Optional[dict] = None


class ReportIngestRequest(BaseModel):
    reports: list[ReportIngestItem]


class ReportSubmitRequest(BaseModel):
    """One report, filed by a person, analysed synchronously.

    Separate from the bulk ingest path on purpose: bulk ingest is a manager-only
    batch job that returns 202 and processes in the background, which is the
    right shape for a nightly export but useless for someone who has just
    written up a near-miss and wants to know whether it mattered.
    """

    site: str
    report_text: str = Field(min_length=15)
    activity: Optional[str] = None
    reporter_role: Optional[str] = None
    observed_at: Optional[datetime] = None


class ReportIngestResponse(BaseModel):
    ingested_count: int
    batch_id: str
    status: str = "processing"


class BatchStatusResponse(BaseModel):
    batch_id: str
    total: int
    classified: int
    status: str  # "processing" | "complete"


# ---------------------------------------------------------------------------
# Reports (list + detail)
# ---------------------------------------------------------------------------
class ReportListItem(BaseModel):
    report_id: str
    site: str
    timestamp: datetime
    sif_potential: bool
    bucket: Bucket
    lsr_tag: str


class PaginatedReports(BaseModel):
    items: list[ReportListItem]
    total: int
    limit: int
    offset: int


class EvidenceSpanItem(BaseModel):
    field: str
    text: str
    span: tuple[int, int]
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ExtractedSpanField(BaseModel):
    text: str
    span: Optional[tuple[int, int]] = None
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedLabelField(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    span: Optional[tuple[int, int]] = None


class ExtractedEnvironmentField(BaseModel):
    category: Optional[str] = None
    text: Optional[str] = None
    span: Optional[tuple[int, int]] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    negated: bool = False
    provenance: str = "exact_span"
    all_detected: list[dict] = Field(default_factory=list)


class ExtractedFields(BaseModel):
    activity: ExtractedSpanField
    hazard: Optional[ExtractedSpanField] = None
    energy_type: ExtractedLabelField
    exposure: ExtractedLabelField
    barrier: Optional[ExtractedSpanField] = None
    barrier_status: ExtractedLabelField
    location: Optional[ExtractedSpanField] = None
    environment: Optional[ExtractedEnvironmentField] = None
    evidence_spans: list[EvidenceSpanItem] = Field(default_factory=list)


class ReasoningStep(BaseModel):
    step: int
    label: str
    detail: str


class Classification(BaseModel):
    model_config = {"protected_namespaces": ()}
    sif_potential: bool
    confidence: float = Field(ge=0.0, le=1.0)
    bucket: Bucket
    lsr_tag: str
    justification: str
    model_version: str
    # Activity -> Energy -> Exposure -> Barrier -> Consequence -> SIF -> LSR.
    # Surfaced on the classification (not buried in the reasoning blob) because
    # the report detail view renders it as the primary explanation of the call.
    reasoning_chain: list[ReasoningStep] = Field(default_factory=list)


class ReportDetail(BaseModel):
    report_id: str
    site: str
    timestamp: datetime
    source: Source
    report_text: str
    extracted_fields: ExtractedFields
    classification: Classification
    review_status: str  # "pending" | "confirmed" | "corrected" | "rejected"
    reasoning: Optional[dict] = None
    site_intelligence: Optional[dict] = None


# ---------------------------------------------------------------------------
# Site Intelligence
# ---------------------------------------------------------------------------
class SiteSummaryItem(BaseModel):
    site_id: str
    canonical_name: str
    region: str
    state: str
    facility_type: str
    latitude: float
    longitude: float
    is_synthetic_prototype: bool
    parent_asset: Optional[str] = None
    description: str = ""
    demonstration_notice: str = "SYNTHETIC DEMONSTRATION DATA"


class SiteListResponse(BaseModel):
    sites: list[SiteSummaryItem]


class SiteDetailResponse(BaseModel):
    site: str
    site_id: str
    region: str
    state: str
    facility_type: str
    total_reports: int
    sif_precursor_count: int
    precursor_density: float
    density_formula: str
    top_lsrs: list[dict]
    top_activities: list[dict]
    barrier_profile: dict
    trend_direction: str
    trend_pct: float
    is_synthetic_prototype: bool
    demonstration_notice: str


class SiteComparisonResponse(BaseModel):
    compared_sites_count: int
    sites: list[dict]
    demonstration_notice: str



# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class RankingRow(BaseModel):
    group: str
    sif_flagged_count: int
    total_reports: int
    density: float
    trend_direction: str  # "up" | "down" | "flat"
    trend_pct: float
    primary_lsr: str
    simple_density: float = 0.0
    # Component breakdown for the composite metric. Always returned so the UI
    # can show WHAT drove a site's score rather than an unexplained number.
    components: dict[str, float] = Field(default_factory=dict)


class MetricWeights(BaseModel):
    """Composite-metric weights. Defaults are EQUAL and explicitly uncalibrated."""

    w1_psif_rate: float = 0.25
    w2_pattern_recurrence: float = 0.25
    w3_energy_magnitude: float = 0.25
    w4_barrier_gap: float = 0.25
    reporting_culture_penalty: float = 0.10


class RankingsResponse(BaseModel):
    metric: str  # "simple" | "composite"
    window_days: int
    rankings: list[RankingRow]
    weights: Optional[MetricWeights] = None  # present only when metric == "composite"
    group_by: str = "site"
    # Always false for now. The frontend renders this next to the number so an
    # uncalibrated composite is never displayed as if it were validated.
    calibrated: bool = False
    note: Optional[str] = None


class ClusterItem(BaseModel):
    cluster_id: str
    pattern_summary: str
    member_report_ids: list[str]
    member_count: int
    sites: list[str]
    primary_lsr: str
    pattern_type: PatternType
    site_count: int = 0
    primary_barrier_failure: Optional[str] = None
    barrier_type: Optional[str] = None
    sif_member_count: int = 0
    sif_share: float = 0.0
    mean_magnitude: float = 0.0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None


class ClusterEdge(BaseModel):
    source: str
    target: str
    similarity: float = Field(ge=0.0, le=1.0)
    cluster_id: Optional[str] = None


class ClustersResponse(BaseModel):
    clusters: list[ClusterItem]
    edges: list[ClusterEdge]
    noise_count: int = 0
    computed_at: Optional[str] = None


class TrendPoint(BaseModel):
    period: str  # ISO date, start of week/month
    count: int
    total_reports: int = 0
    sif_count: int = 0
    precursor_rate: float = 0.0


class TrendAlert(BaseModel):
    period: str
    message: str
    method: str  # "CUSUM" | "EWMA"
    count: float = 0.0
    baseline_mean: float = 0.0
    threshold: float = 0.0
    severity: str = "medium"


class TrendsResponse(BaseModel):
    series: list[TrendPoint]
    alerts: list[TrendAlert]
    granularity: str = "weekly"
    cusum: dict = Field(default_factory=dict)
    ewma: dict = Field(default_factory=dict)
    # Fixed copy stating what SPC can and cannot claim. Rendered adjacent to
    # the chart, never as a hover-only tooltip.
    method_note: Optional[str] = None


class DashboardSummary(BaseModel):
    total_reports: int
    high_priority_pattern_count: int
    reports_pending_review: int
    last_ingested_at: Optional[datetime] = None
    # Live distribution across the 4 confidence buckets. The console renders
    # this directly, so it must come from the DB rather than being recomputed
    # (and possibly disagreeing) on the client.
    bucket_counts: dict[str, int] = Field(default_factory=dict)
    sif_flagged_count: int = 0
    sif_rate: float = 0.0
    site_count: int = 0
    emerging_pattern_count: int = 0


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------
class ReviewActionRequest(BaseModel):
    action: ReviewActionType
    corrected_sif_potential: Optional[bool] = None
    corrected_lsr_tag: Optional[str] = None
    reviewer_notes: Optional[str] = None


class ReviewActionResponse(BaseModel):
    report_id: str
    review_action_id: str
    status: str = "recorded"
    promoted_to_training_queue: bool


# ---------------------------------------------------------------------------
# Recommendations / intervention engine
# ---------------------------------------------------------------------------
class EvidenceSummary(BaseModel):
    report_count: int
    site_count: int
    window_days: int
    trend_pct: float


class RecommendationListItem(BaseModel):
    pattern_id: str
    title: str
    evidence_summary: EvidenceSummary
    primary_barrier_failure: str
    priority: str  # "HIGH" | "MEDIUM" | "LOW"


class RecommendationsResponse(BaseModel):
    recommendations: list[RecommendationListItem]


class AssociationRule(BaseModel):
    antecedent_text: str
    consequent_text: str
    support: float
    confidence: float
    baseline: float
    lift: float
    report_count: int
    statement: str


class AssociationsResponse(BaseModel):
    rules: list[AssociationRule]
    note: str = (
        "Co-occurrence in reported observations. Not a causal relationship."
    )


class BarrierFailureRow(BaseModel):
    activity: str
    barrier_failure_mode: str
    report_count: int
    sif_count: int
    sif_share: float


class BarrierFailuresResponse(BaseModel):
    items: list[BarrierFailureRow]


class RecomputeResponse(BaseModel):
    clusters_written: int
    reports_considered: int
    elapsed_seconds: float
    status: str = "complete"


class EvidenceDetail(BaseModel):
    report_count: int
    site_count: int
    window_days: int
    member_report_ids: list[str]
    # Open-ended counts keyed by evidence type (barrier_explicitly_absent,
    # direct_personnel_exposure, failure_mode::<mode>, ...). Previously three
    # hardcoded isolation-specific fields, which could not describe a fall-
    # protection or gas-testing pattern at all.
    breakdown: dict[str, int] = Field(default_factory=dict)
    sites: list[str]
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None


class RecommendedIntervention(BaseModel):
    rank: int
    control_level: str  # "engineering" | "administrative" | "procedural" | "training"
    priority: str
    action: str


class RecommendationDetail(BaseModel):
    pattern_id: str
    title: str
    evidence: EvidenceDetail
    recommended_interventions: list[RecommendedIntervention]
    expected_objective: str


class ActionPlanRequest(BaseModel):
    selected_intervention_ranks: list[int]
    target_sites: list[str]
    planned_start_date: date


class ActionPlanResponse(BaseModel):
    action_plan_id: str
    pattern_id: str
    status: str  # "planned" | "in_progress" | "complete"


class ActionPlanUpdateRequest(BaseModel):
    actual_start_date: Optional[date] = None
    status: Optional[str] = None


# ---------------------------------------------------------------------------
# Intervention / outcome tracking
# ---------------------------------------------------------------------------
class ImpactBefore(BaseModel):
    window_days: int
    precursor_rate: float


class ImpactWeek(BaseModel):
    week: int
    precursor_rate: float


class ImpactResponse(BaseModel):
    action_plan_id: str
    pattern_id: str
    intervention_start_date: date
    before: ImpactBefore
    after_weekly: list[ImpactWeek]
    pct_change: float
    disclaimer: str = (
        "Reported precursor frequency change following the intervention. "
        "Historical association only — not a causal claim."
    )


# ---------------------------------------------------------------------------
# Audit / admin / health / auth
# ---------------------------------------------------------------------------
class AuditLogEntry(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    action: str
    actor: str
    timestamp: datetime


class PaginatedAuditLog(BaseModel):
    items: list[AuditLogEntry]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    status: str = "ok"
    model_version: str
    db: str
    active_sif_model: Optional[str] = "baseline2"
    mlp_available: Optional[bool] = True


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    role: Role


class MeResponse(BaseModel):
    username: str
    role: Role


# ---------------------------------------------------------------------------
# Live Safety Vision
# ---------------------------------------------------------------------------
class VisionSeverity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class VisionEventStatus(str, Enum):
    active = "active"
    acknowledged = "acknowledged"


class VisionSourceType(str, Enum):
    webcam = "webcam"
    demo_video = "demo_video"
    rtsp = "rtsp"


class VisionDetectedObject(BaseModel):
    class_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: list[float]  # [x1, y1, x2, y2] normalized 0..1


class VisionRoi(BaseModel):
    name: str
    roi_type: str
    points: list[list[float]]
    hazard_context: str
    lsr_tag: str


class VisionCamera(BaseModel):
    camera_id: str
    camera_name: str
    site_id: str
    rois: list[VisionRoi] = Field(default_factory=list)


class VisionCamerasResponse(BaseModel):
    cameras: list[VisionCamera]
    demo_notice: str = (
        "Demo camera identifiers for the SIH demonstration — not a claim of "
        "installed OIL India CCTV infrastructure."
    )


class VisionStartRequest(BaseModel):
    site_id: str
    camera_id: str
    source_type: VisionSourceType
    rtsp_url: Optional[str] = None


class VisionStartResponse(BaseModel):
    camera_id: str
    site_id: str
    active: bool
    source_type: VisionSourceType
    model_config = {"protected_namespaces": ()}
    model_name: str
    device: str
    model_ready: bool
    model_error: Optional[str] = None
    demo_notice: str


class VisionStopRequest(BaseModel):
    camera_id: str


class VisionStopResponse(BaseModel):
    camera_id: str
    active: bool


class VisionAnalyzeFrameRequest(BaseModel):
    site_id: str
    camera_id: str
    # ~8M base64 chars decodes to ~6MB — a 640px-wide JPEG frame at quality
    # 0.6 is tens of KB, so this is generous headroom while still bounding
    # memory/CPU spent decoding a single request on a publicly reachable
    # endpoint (this is a live camera feed, not a file upload).
    image_base64: str = Field(min_length=10, max_length=8_000_000)


class VisionSafetyEvent(BaseModel):
    event_id: str
    timestamp: datetime
    site_id: str
    camera_id: str
    camera_name: str
    event_type: str
    severity: VisionSeverity
    confidence: float = Field(ge=0.0, le=1.0)
    objects: list[VisionDetectedObject] = Field(default_factory=list)
    evidence: str
    roi: Optional[str] = None
    observed: str
    inference: str
    sif_relevance: str
    lsr_tag: str
    status: VisionEventStatus = VisionEventStatus.active
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


class VisionAnalyzeFrameResponse(BaseModel):
    camera_id: str
    site_id: str
    frame_ts: datetime
    people_count: int
    vehicle_count: int
    detections: list[VisionDetectedObject] = Field(default_factory=list)
    new_events: list[VisionSafetyEvent] = Field(default_factory=list)
    model_config = {"protected_namespaces": ()}
    model_name: str
    device: str
    skipped: bool = False


class VisionStatusResponse(BaseModel):
    camera_id: str
    site_id: Optional[str] = None
    active: bool
    source_type: Optional[str] = None
    people_count: int = 0
    vehicle_count: int = 0
    active_hazards: int = 0
    high_priority_hazards: int = 0
    model_config = {"protected_namespaces": ()}
    model_name: str
    device: str
    model_ready: bool
    model_error: Optional[str] = None
    last_frame_at: Optional[datetime] = None
    demo_notice: str


class VisionEventsResponse(BaseModel):
    events: list[VisionSafetyEvent]
    total: int
