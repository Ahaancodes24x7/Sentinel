export type UserRole = 'hse_manager' | 'hse_analyst' | 'hse_reviewer' | 'auditor';

export interface User {
  username: string;
  role: UserRole;
  name: string;
  avatar?: string;
  organization: string;
  site?: string;
}

export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type Bucket = 'HIGH_CONF_SIF' | 'LOW_CONF_REVIEW' | 'NEEDS_MORE_INFO' | 'NON_SIF';

// PS 26165: 3-Way Barrier State
export type BarrierState3Way = 'CONFIRMED_EFFECTIVE' | 'UNCERTAIN_DEGRADED' | 'ABSENT_NOT_CONFIRMED';

export type Source = 'synthetic' | 'real';

export interface ExtractedSpan {
  text: string;
  span: [number, number];
  confidence: number;
}

export interface ExtractedLabel {
  label?: string;
  confidence: number;
  text?: string;
  span?: [number, number];
}

export interface ExtractedFields {
  activity?: ExtractedSpan;
  energy_type?: ExtractedLabel;
  barrier?: ExtractedLabel;
  barrier_status?: ExtractedLabel | { status: BarrierState3Way; text: string; confidence: number };
  exposure?: ExtractedSpan;
  outcome?: ExtractedSpan;
  credible_consequence?: ExtractedLabel;
  [key: string]: any;
}

export interface Classification {
  sif_potential: boolean;
  confidence: number;
  bucket: Bucket;
  lsr_tag: string;
  justification: string;
  model_version: string;
  risk_level: RiskLevel;
  hazard: string;
  failed_barrier: string;
  barrier_state_3way?: BarrierState3Way;
}

export interface ReportItem {
  report_id: string;
  site: string;
  timestamp: string;
  source: Source;
  report_text: string;
  actual_outcome?: 'NO_INJURY' | 'MINOR_INJURY' | 'SERIOUS_INJURY';
  extracted_fields?: ExtractedFields;
  classification?: Classification;
  review_status: 'pending' | 'reviewed' | 'escalated';
  sif_potential: boolean;
  bucket: Bucket;
  lsr_tag: string;
  risk_level: RiskLevel;
  hazard: string;
  failed_barrier: string;
  barrier_state_3way?: BarrierState3Way;
  why_flagged_checklist?: string[];
  ontology_mapping?: {
    energy_type: string;
    activity: string;
    lsr: string;
  };
}

export interface ReasoningChainStep {
  id: 'activity' | 'energy' | 'barrier' | 'exposure' | 'consequence' | 'lsr';
  title: string;
  subtitle: string;
  value: string;
  confidence: number;
  source_text: string;
  ontology_mapping: string;
  status?: BarrierState3Way | 'detected' | 'critical';
}

export interface DashboardSummary {
  total_reports: number;
  total_reports_trend: number;
  high_risk_reports: number;
  high_risk_trend: number;
  critical_reports: number;
  sif_precursors: number;
  sif_precursors_trend: number;
  high_confidence_sif: number;
  needs_hse_review: number;
  high_conf_non_sif: number;
  insufficient_detail_count: number;
  failed_barriers: number;
  failed_barriers_trend: number;
  open_interventions: number;
  open_interventions_critical: number;
  high_priority_pattern_count: number;
  reports_pending_review: number;
  last_ingested_at: string;
  psif_rate: number;
  high_energy_exposure_rate: number;
  barrier_failure_rate: number;
}

export interface RankingRow {
  group: string;
  sif_flagged_count: number;
  total_reports: number;
  density: number;
  trend_direction: 'up' | 'down' | 'flat';
  trend_pct: number;
  primary_lsr: string;
  risk_score: number;
  barrier_failures: number;
  risk_level: RiskLevel;
  psif_rate: number;
}

export interface PrecursorCluster {
  cluster_id: string;
  pattern_summary: string;
  member_report_ids: string[];
  member_count: number;
  sites: string[];
  primary_lsr: string;
  pattern_type: 'established' | 'emerging' | 'sporadic_high_severity';
  risk_level: RiskLevel;
  growth_rate: number;
  primary_barrier: string;
  why_it_matters: string;
  timeline?: { date: string; count: number }[];
  differently_worded_reports?: { id: string; text: string; site: string }[];
}

export interface ClusterNode {
  id: string;
  label: string;
  type: 'activity' | 'energy' | 'barrier' | 'failure_mode' | 'site' | 'lsr';
  reportsCount: number;
}

export interface ClusterEdge {
  source: string;
  target: string;
  relation: string; // "associated with", "co-occurs with", "observed at"
}

export interface Matrix2DItem {
  id: string;
  pattern: string;
  barrier: string;
  recurrence: 'RARE' | 'RECURRING';
  severity: 'HIGH_SIF' | 'LOWER_RISK';
  reportCount: number;
  lsr: string;
  sitesCount: number;
}

export interface EarlyWarningSignal {
  id: string;
  barrier: string;
  site: string;
  baseline_rate: number;
  current_rate: number;
  pct_increase: number;
  status: 'UNUSUAL_INCREASE' | 'ELEVATED' | 'NORMAL';
  recommendation: string;
  historical_data: { date: string; baseline: number; actual: number }[];
}

export interface ReportQualityStats {
  complete_count: number;
  incomplete_count: number;
  missing_location_pct: number;
  missing_activity_pct: number;
  missing_barrier_pct: number;
  missing_exposure_pct: number;
}

export interface DemoScenario {
  id: string;
  name: string;
  subtitle: string;
  reportId: string;
  description: string;
}

export interface TrendPoint {
  period: string;
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  sif_count: number;
}

export interface TrendAlert {
  period: string;
  message: string;
  method: string;
  severity: RiskLevel;
}

export interface LifeSavingRule {
  id: string;
  name: string;
  compliance_pct: number;
  violations_count: number;
  trend: 'improving' | 'deteriorating' | 'stable';
  risk_level: RiskLevel;
  icon: string;
  description: string;
}

export interface RecommendedIntervention {
  rank: number;
  control_level: 'engineering' | 'administrative' | 'ppe' | 'training';
  priority: RiskLevel;
  action: string;
}

export interface Recommendation {
  pattern_id: string;
  title: string;
  priority: RiskLevel;
  reason: string;
  impact: string;
  confidence: number;
  owner: string;
  status: 'recommended' | 'assigned' | 'in_progress' | 'completed';
  primary_barrier_failure: string;
  evidence_summary: {
    report_count: number;
    site_count: number;
    window_days: number;
    trend_pct: number;
  };
  recommended_interventions: RecommendedIntervention[];
  expected_objective: string;
  target_sites: string[];
  created_at: string;
}

export interface ActionPlan {
  action_plan_id: string;
  pattern_id: string;
  selected_interventions: number[];
  target_sites: string[];
  planned_start_date: string;
  actual_start_date?: string;
  status: 'planned' | 'in_progress' | 'completed';
  created_by: string;
  created_at: string;
}

export interface ClassifierMetrics {
  precision: number;
  recall: number;
  f1: number;
  accuracy: number;
}

export interface ModelPerformanceData {
  sif_classifier: ClassifierMetrics & { pr_auc: number; f2: number };
  lsr_classifier: { top1_accuracy: number; top2_accuracy: number; per_class_recall: number };
  extraction_f1: { activity_f1: number; energy_f1: number; barrier_f1: number; exposure_f1: number };
  calibration: { expected_calibration_error: number };
  confusion_matrix: {
    tp: number;
    fp: number;
    fn: number;
    tn: number;
  };
  model_version: string;
  last_trained: string;
  dataset_size: number;
  inference_latency_ms: number;
}

export interface AuditLogEntry {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  actor: string;
  timestamp: string;
  details?: string;
  model_version?: string;
  lsr_mapping?: string;
  sif_classification?: string;
  confidence?: number;
}

export interface BarrierStat {
  barrier: string;
  failures: number;
  severity: RiskLevel;
  trend_pct: number;
  sites_affected: number;
  last_detected: string;
  description: string;
  category: string;
  state_3way: BarrierState3Way;
}

