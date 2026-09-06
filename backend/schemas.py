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


class ReportIngestRequest(BaseModel):
    reports: list[ReportIngestItem]


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


class ExtractedSpanField(BaseModel):
    text: str
    span: tuple[int, int]
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedLabelField(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    span: Optional[tuple[int, int]] = None


class ExtractedFields(BaseModel):
    activity: ExtractedSpanField
    energy_type: ExtractedLabelField
    barrier_status: ExtractedLabelField
    exposure: ExtractedLabelField


class Classification(BaseModel):
    model_config = {"protected_namespaces": ()}
    sif_potential: bool
    confidence: float = Field(ge=0.0, le=1.0)
    bucket: Bucket
    lsr_tag: str
    justification: str
    model_version: str


class ReportDetail(BaseModel):
    report_id: str
    site: str
    timestamp: datetime
    source: Source
    report_text: str
    extracted_fields: ExtractedFields
    classification: Classification
    review_status: str  # "pending" | "confirmed" | "corrected" | "rejected"


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


class MetricWeights(BaseModel):
    w1_severity_adjusted_rate: float = 0.34
    w2_recurrence: float = 0.33
    w3_severity_weighting: float = 0.33


class RankingsResponse(BaseModel):
    metric: str  # "simple" | "composite"
    window_days: int
    rankings: list[RankingRow]
    weights: Optional[MetricWeights] = None  # present only when metric == "composite"


class ClusterItem(BaseModel):
    cluster_id: str
    pattern_summary: str
    member_report_ids: list[str]
    member_count: int
    sites: list[str]
    primary_lsr: str
    pattern_type: PatternType


class ClusterEdge(BaseModel):
    source: str
    target: str
    similarity: float = Field(ge=0.0, le=1.0)


class ClustersResponse(BaseModel):
    clusters: list[ClusterItem]
    edges: list[ClusterEdge]


class TrendPoint(BaseModel):
    period: str  # ISO date, start of week/month
    count: int


class TrendAlert(BaseModel):
    period: str
    message: str
    method: str  # "CUSUM" | "EWMA"


class TrendsResponse(BaseModel):
    series: list[TrendPoint]
    alerts: list[TrendAlert]


class DashboardSummary(BaseModel):
    total_reports: int
    high_priority_pattern_count: int
    reports_pending_review: int
    last_ingested_at: datetime


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


class EvidenceBreakdown(BaseModel):
    mentions_missing_isolation: int
    involves_maintenance: int
    involves_equipment_opening: int


class EvidenceDetail(BaseModel):
    report_count: int
    site_count: int
    window_days: int
    member_report_ids: list[str]
    breakdown: EvidenceBreakdown
    sites: list[str]


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
