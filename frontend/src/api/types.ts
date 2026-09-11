/** Wire types — these mirror backend/schemas.py exactly. */

export type Bucket = 'HIGH_CONF_SIF' | 'LOW_CONF_REVIEW' | 'HIGH_CONF_NON_SIF' | 'NEEDS_MORE_INFO';
export type PatternType = 'established' | 'emerging' | 'sporadic_high_severity';
export type Role = 'hse_reviewer' | 'hse_manager' | 'auditor';
export type Priority = 'HIGH' | 'MEDIUM' | 'LOW';
export type BarrierStatus =
  | 'confirmed_present'
  | 'uncertain'
  | 'explicitly_absent'
  | 'not_mentioned';

export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ReportListItem {
  report_id: string;
  site: string;
  timestamp: string;
  sif_potential: boolean;
  bucket: Bucket;
  lsr_tag: string;
  source?: string;
  confidence?: number;
  /** Present on reports the CCTV pipeline filed by itself. */
  priority?: string | null;
  auto_filed?: boolean;
}

export interface SpanField {
  text?: string;
  label?: string;
  span?: [number, number] | null;
  confidence?: number;
}

export interface EvidenceSpanItem {
  field: string;
  text: string;
  span: [number, number];
  confidence: number;
}

export interface ExtractedFields {
  activity?: SpanField;
  energy_type?: SpanField;
  barrier_status?: SpanField;
  barrier?: SpanField;
  exposure?: SpanField;
  hazard?: SpanField;
  location?: SpanField;
  environment?: SpanField;
  evidence_spans?: EvidenceSpanItem[];
  [key: string]: unknown;
}

export interface Classification {
  sif_potential: boolean;
  confidence: number;
  bucket: Bucket;
  lsr_tag: string;
  justification: string;
  model_version: string;
  reasoning_chain?: { step: number; label: string; detail: string }[];
  /** Whether the active learned classifier (baseline2 / mlp / the fine-tuned
   *  transformer) agrees with the deterministic SCL verdict on this report.
   *  A confident disagreement demotes a HIGH_CONF_* bucket to LOW_CONF_REVIEW
   *  rather than being silently discarded — see routing.route_prediction. */
  model_agreement?: {
    available: boolean;
    agrees: boolean | null;
    model_sif_potential: boolean | null;
    model_confidence: number | null;
    model_version: string | null;
    escalated: boolean;
  } | null;
  decision_factors?: Record<string, unknown>;
  /**
   * Present only on complaints the CCTV pipeline filed by itself. A reviewer
   * opening one has to be able to see, without leaving the page, that no human
   * wrote it, which camera event produced it, and why it carries the priority
   * it does.
   */
  auto_filed?: boolean | null;
  priority?: string | null;
  priority_label?: string | null;
  priority_rationale?: string | null;
  recommended_action?: string | null;
  vision_event_id?: string | null;
  vision_event_type?: string | null;
  vision_severity?: string | null;
  vision_confidence?: number | null;
  vision_camera_id?: string | null;
  vision_camera_name?: string | null;
}

export interface ReportDetail {
  report_id: string;
  site: string;
  timestamp: string;
  source: string;
  report_text: string;
  extracted_fields: ExtractedFields;
  classification: Classification;
  review_status: string;
}

export interface DashboardSummary {
  total_reports: number;
  high_priority_pattern_count: number;
  reports_pending_review: number;
  last_ingested_at?: string | null;
  bucket_counts: Record<string, number>;
  sif_flagged_count: number;
  sif_rate: number;
  site_count: number;
  emerging_pattern_count: number;
}

export interface RankingRow {
  group: string;
  sif_flagged_count: number;
  total_reports: number;
  density: number;
  simple_density: number;
  trend_direction: 'up' | 'down' | 'flat';
  trend_pct: number;
  primary_lsr: string;
  components: Record<string, number>;
}

export interface RankingsResponse {
  metric: 'simple' | 'composite';
  window_days: number;
  group_by: string;
  rankings: RankingRow[];
  weights?: Record<string, number> | null;
  calibrated: boolean;
  note?: string | null;
}

export interface ClusterItem {
  cluster_id: string;
  pattern_summary: string;
  member_report_ids: string[];
  member_count: number;
  sites: string[];
  site_count: number;
  primary_lsr: string;
  primary_barrier_failure?: string | null;
  barrier_type?: string | null;
  pattern_type: PatternType;
  sif_member_count: number;
  sif_share: number;
  mean_magnitude: number;
  first_seen?: string | null;
  last_seen?: string | null;
}

export interface ClusterEdge {
  source: string;
  target: string;
  similarity: number;
  cluster_id?: string | null;
}

export interface ClustersResponse {
  clusters: ClusterItem[];
  edges: ClusterEdge[];
  noise_count: number;
  computed_at?: string | null;
}

export interface TrendPoint {
  period: string;
  count: number;
  total_reports: number;
  sif_count: number;
  precursor_rate: number;
}

export interface TrendAlert {
  period: string;
  message: string;
  method: string;
  count: number;
  baseline_mean: number;
  threshold: number;
  severity: string;
}

export interface TrendsResponse {
  series: TrendPoint[];
  alerts: TrendAlert[];
  granularity: string;
  cusum: { upper?: number[]; threshold?: number; baseline_mean?: number; signals?: number[] };
  ewma: { ewma?: number[]; upper_limit?: number[]; lower_limit?: number[]; signals?: number[] };
  method_note?: string | null;
}

export interface AssociationRule {
  antecedent_text: string;
  consequent_text: string;
  support: number;
  confidence: number;
  baseline: number;
  lift: number;
  report_count: number;
  statement: string;
}

export interface AssociationsResponse {
  rules: AssociationRule[];
  note: string;
}

export interface BarrierFailureRow {
  activity: string;
  barrier_failure_mode: string;
  report_count: number;
  sif_count: number;
  sif_share: number;
}

export interface RecommendationListItem {
  pattern_id: string;
  title: string;
  evidence_summary: {
    report_count: number;
    site_count: number;
    window_days: number;
    trend_pct: number;
  };
  primary_barrier_failure: string;
  priority: Priority;
  /** Curated barrier this pattern is filed under — the key into the intervention library. */
  barrier_type: string;
  /** IOGP Life-Saving Rule this pattern's controlling energy types map to. "N/A" if unresolved. */
  primary_lsr: string;
}

export interface RecommendedIntervention {
  rank: number;
  control_level: string;
  priority: string;
  action: string;
  /** Failure modes (ontology vocabulary) this control is curated to address. */
  addresses: string[];
  /** Of those, the ones THIS pattern's reports actually recorded. */
  matched_failure_modes: string[];
  /** How many of this pattern's reports mentioned a matched failure mode. */
  evidence_match_count: number;
}

export interface RecommendationDetail {
  pattern_id: string;
  title: string;
  evidence: {
    report_count: number;
    site_count: number;
    window_days: number;
    member_report_ids: string[];
    breakdown: Record<string, number>;
    sites: string[];
    first_seen?: string | null;
    last_seen?: string | null;
  };
  recommended_interventions: RecommendedIntervention[];
  expected_objective: string;
  barrier_type: string;
  primary_lsr: string;
}

/* -------------------------------------------------------------------------
 * Site registry / Operations Map
 * ---------------------------------------------------------------------- */

export interface SiteSummaryItem {
  site_id: string;
  canonical_name: string;
  region: string;
  state: string;
  facility_type: string;
  latitude: number;
  longitude: number;
  is_synthetic_prototype: boolean;
  parent_asset?: string | null;
  description: string;
  demonstration_notice: string;
}

export interface SiteListResponse {
  sites: SiteSummaryItem[];
}

export interface SiteDetailResponse {
  site: string;
  site_id: string;
  region: string;
  state: string;
  facility_type: string;
  total_reports: number;
  sif_precursor_count: number;
  precursor_density: number;
  density_formula: string;
  top_lsrs: { lsr: string; count: number; share: number }[];
  top_activities: { activity: string; count: number }[];
  barrier_profile: Record<string, number>;
  trend_direction: 'up' | 'down' | 'flat';
  trend_pct: number;
  is_synthetic_prototype: boolean;
  demonstration_notice: string;
}

export interface HealthResponse {
  status: string;
  model_version: string;
  db: string;
  active_sif_model?: string;
  mlp_available?: boolean;
}

export interface AuditEntry {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  actor: string;
  timestamp: string;
}

export interface OntologyEnergyType {
  is_high_energy: boolean;
  lsr_tag: string;
  magnitude_class: number;
  keywords?: string[];
}

export interface Ontology {
  version?: string;
  life_saving_rules?: Record<string, { icon?: string; description?: string }>;
  energy_types?: Record<string, OntologyEnergyType>;
  barrier_types?: Record<
    string,
    {
      controls_energy: string[];
      control_level: string;
      is_direct_control: boolean;
      failure_modes: string[];
    }
  >;
  activities?: string[];
  activity_energy_map?: Record<string, string[]>;
  sites?: { name: string; type: string; region: string; workforce: number }[];
  density_metric?: { calibrated: boolean; note: string; weights: Record<string, number> };
  [key: string]: unknown;
}

export const BUCKET_META: Record<Bucket, { label: string; short: string; tone: string }> = {
  HIGH_CONF_SIF: { label: 'High-confidence precursor', short: 'PRIORITY', tone: 'critical' },
  LOW_CONF_REVIEW: { label: 'Needs review', short: 'REVIEW', tone: 'high' },
  NEEDS_MORE_INFO: { label: 'Insufficient detail', short: 'INCOMPLETE', tone: 'medium' },
  HIGH_CONF_NON_SIF: { label: 'Cleared', short: 'CLEARED', tone: 'low' },
};

/* -------------------------------------------------------------------------
 * CCTV hazard monitoring
 * ---------------------------------------------------------------------- */

export type VisionSeverity = 'critical' | 'high' | 'medium' | 'low';
export type VisionPriority = 'P1' | 'P2' | 'P3' | 'P4';
export type VisionEventStatus = 'active' | 'acknowledged';
export type VisionSourceType = 'webcam' | 'demo_video' | 'rtsp';

export interface VisionDetectedObject {
  class_name: string;
  confidence: number;
  bbox: [number, number, number, number];
}

export interface VisionRoi {
  name: string;
  roi_type: string;
  points: number[][];
  hazard_context: string;
  lsr_tag: string;
}

export interface VisionCamera {
  camera_id: string;
  camera_name: string;
  site_id: string;
  rois: VisionRoi[];
}

export interface VisionCamerasResponse {
  cameras: VisionCamera[];
  demo_notice: string;
}

/** A pixel area a scene analyzer flagged - flame, plume, falling mass, casualty. */
export interface VisionRegion {
  kind: string;
  bbox: [number, number, number, number];
  score: number;
  area_ratio: number;
}

/** Continuous per-frame hazard indices, rendered live so an operator can watch
 *  an index climb before it crosses a threshold. */
export interface VisionSignals {
  fire_score: number;
  smoke_score: number;
  motion_score: number;
  visibility: number;
  visibility_drop: number;
  fire_active: boolean;
  smoke_active: boolean;
  visibility_active: boolean;
  person_count: number;
  occupancy_delta: number;
  regions: VisionRegion[];
  frame_index: number;
  analyzer_ready: boolean;
}

export interface VisionSafetyEvent {
  event_id: string;
  timestamp: string;
  site_id: string;
  camera_id: string;
  camera_name: string;
  event_type: string;
  severity: VisionSeverity;
  confidence: number;
  objects: VisionDetectedObject[];
  evidence: string;
  roi?: string | null;
  observed: string;
  inference: string;
  sif_relevance: string;
  lsr_tag: string;
  hazard_class: string;
  regions: VisionRegion[];
  status: VisionEventStatus;
  acknowledged_by?: string | null;
  acknowledged_at?: string | null;
  /** The complaint this event filed automatically. Null only if filing itself
   *  failed, in which case auto_report_error says why. */
  auto_report_id?: string | null;
  auto_report_priority?: VisionPriority | null;
  auto_report_priority_label?: string | null;
  auto_report_bucket?: string | null;
  auto_report_sif?: boolean | null;
  auto_report_error?: string | null;
}

export interface VisionEventsResponse {
  events: VisionSafetyEvent[];
  total: number;
}

export interface VisionStatusResponse {
  camera_id: string;
  site_id?: string | null;
  active: boolean;
  source_type?: string | null;
  people_count: number;
  vehicle_count: number;
  active_hazards: number;
  high_priority_hazards: number;
  auto_reports_filed: number;
  frames_processed: number;
  events_raised: number;
  model_name: string;
  device: string;
  model_ready: boolean;
  model_error?: string | null;
  last_frame_at?: string | null;
  signals: VisionSignals;
  demo_notice: string;
}

export interface VisionAnalyzeFrameResponse {
  camera_id: string;
  site_id: string;
  frame_ts: string;
  people_count: number;
  vehicle_count: number;
  detections: VisionDetectedObject[];
  new_events: VisionSafetyEvent[];
  model_name: string;
  device: string;
  signals: VisionSignals;
  latency_ms: number;
  skipped?: boolean;
}

export interface VisionStartResponse {
  camera_id: string;
  site_id: string;
  active: boolean;
  source_type: VisionSourceType;
  model_name: string;
  device: string;
  model_ready: boolean;
  model_error?: string | null;
  demo_notice: string;
}

export const VISION_SEVERITY_TONE: Record<VisionSeverity, 'critical' | 'high' | 'medium' | 'low'> = {
  critical: 'critical',
  high: 'high',
  medium: 'medium',
  low: 'low',
};

export const VISION_PRIORITY_TONE: Record<VisionPriority, 'critical' | 'high' | 'medium' | 'low'> = {
  P1: 'critical',
  P2: 'high',
  P3: 'medium',
  P4: 'low',
};

/** Operator-facing name for each hazard family the camera can raise. */
export const VISION_EVENT_LABEL: Record<string, string> = {
  fire_detected: 'Fire detected',
  smoke_detected: 'Smoke detected',
  visibility_loss: 'Visibility loss',
  person_fall: 'Worker fall',
  person_down_immobile: 'Worker down - immobile',
  struck_by_falling_object: 'Struck by falling object',
  falling_object: 'Falling object / roof fall',
  crowd_dispersal: 'Sudden evacuation',
  crowd_surge: 'Sudden crowding',
  restricted_zone_entry: 'Restricted zone entry',
  lifting_zone_entry: 'Lifting zone entry',
  vehicle_person_proximity: 'Vehicle-person proximity',
};

export const BARRIER_META: Record<BarrierStatus, { label: string; tone: string; gap: string }> = {
  explicitly_absent: { label: 'Absent', tone: 'critical', gap: '1.0' },
  uncertain: { label: 'Unverified', tone: 'high', gap: '0.6' },
  not_mentioned: { label: 'Not recorded', tone: 'medium', gap: '—' },
  confirmed_present: { label: 'Confirmed', tone: 'low', gap: '0.0' },
};
