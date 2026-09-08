/**
 * Single source of copy + data for the marketing landing page.
 * Pulls the domain facts (buckets, roles, capabilities) from the same modules
 * the console uses, so the landing page can never drift from the product.
 */
import { ROLE_LABEL, type Capability } from "@/lib/rbac";
import { BUCKET_META, BUCKETS } from "@/lib/ontology";
import type { Role } from "@/lib/api/schemas";

export { ROLE_LABEL };

export const NAV_LINKS = [
  { href: "#pipeline", label: "Pipeline" },
  { href: "#capabilities", label: "Console" },
  { href: "#triage", label: "Triage" },
  { href: "#roles", label: "Access" },
] as const;

export const HERO = {
  kicker: "SIF Precursor Monitor · SIH PS 26165",
  title: "Find the serious-injury precursors hiding in near-miss reports.",
  body: "Sentinel reads free-text safety reports — multilingual, code-mixed, abbreviated — and surfaces the ones that carried Serious Injury & Fatality potential, with calibrated confidence and a human review loop.",
} as const;

export const METRICS = [
  { value: "7", label: "Pipeline stages, ingest to action" },
  { value: "4", label: "Triage buckets" },
  { value: "8", label: "LSR categories tracked" },
  { value: "3", label: "Role-gated access levels" },
] as const;

export interface PipelineStage {
  step: string;
  name: string;
  detail: string;
}

export const PIPELINE: PipelineStage[] = [
  {
    step: "01",
    name: "Ingest",
    detail:
      "Near-miss and incident reports arrive from site systems in mixed languages and shorthand.",
  },
  {
    step: "02",
    name: "Preprocess",
    detail:
      "Typo correction, abbreviation expansion and code-mixed normalisation on every report.",
  },
  {
    step: "03",
    name: "Extract",
    detail:
      "NER and field classifiers pull activity, hazard, energy type, exposure and barrier state.",
  },
  {
    step: "04",
    name: "Reason",
    detail:
      "Ontology rules, credible-consequence and consistency checks run over the extracted frame.",
  },
  {
    step: "05",
    name: "Classify",
    detail:
      "SIF potential and LSR category assigned with a calibrated confidence score.",
  },
  {
    step: "06",
    name: "Route",
    detail:
      "High-confidence results file automatically; low-confidence ones go to the review queue.",
  },
  {
    step: "07",
    name: "Act",
    detail:
      "Clustering, CUSUM trend detection, site rankings and ranked intervention recommendations.",
  },
];

export const PIPELINE_LOOP =
  "Reviewer confirmations and corrections feed the next training round.";

export interface Capsule {
  title: string;
  detail: string;
  tag: string;
}

export const CAPABILITIES: Capsule[] = [
  {
    title: "Report triage",
    detail:
      "Every report lands in one of four buckets with per-field confidence and span-level evidence.",
    tag: "/reports",
  },
  {
    title: "Review queue",
    detail:
      "Low-confidence and needs-more-info reports, with a confirm / correct / reject form and a two-reviewer promotion gate.",
    tag: "/review-queue",
  },
  {
    title: "Rankings",
    detail:
      "Simple and composite precursor-rate rankings by site or activity, over a rolling window.",
    tag: "/rankings",
  },
  {
    title: "Clusters",
    detail:
      "Node-link view of recurring precursor patterns, sized by member count and typed by pattern class.",
    tag: "/clusters",
  },
  {
    title: "Trends",
    detail:
      "Weekly and monthly precursor-rate series with CUSUM alert markers and verbatim alert context.",
    tag: "/trends",
  },
  {
    title: "Action center",
    detail:
      "Evidence trail to ranked interventions, action plans, and before / after impact tracking.",
    tag: "/action-center",
  },
  {
    title: "Audit log",
    detail:
      "Every classification, review action and plan change, filterable and timestamp-sorted.",
    tag: "/audit-log",
  },
  {
    title: "Synthetic-data guardrail",
    detail:
      "Any screen showing report data carries a persistent synthetic-vs-real banner. It is a guardrail, not a footnote.",
    tag: "guardrail",
  },
];

export const BUCKET_LIST = BUCKETS.map((key) => ({ key, ...BUCKET_META[key] }));

export const ROLE_CAPS: { cap: Capability; label: string }[] = [
  { cap: "view_reports", label: "View reports & classifications" },
  { cap: "view_review_queue", label: "Open the review queue" },
  { cap: "act_review_queue", label: "Record review actions" },
  { cap: "ingest_data", label: "Ingest new report batches" },
  { cap: "view_rankings", label: "Rankings, clusters & trends" },
  { cap: "view_action_center", label: "SIF action center" },
  { cap: "create_action_plan", label: "Create & update action plans" },
  { cap: "view_audit_log", label: "Read the audit log" },
];

export const ROLES: Role[] = ["hse_reviewer", "hse_manager", "auditor"];

export const FOOTER_NOTE =
  "Demo build. Runs against a synthetic report dataset unless connected to a live backend. Synthetic rows are labelled on every data screen.";
