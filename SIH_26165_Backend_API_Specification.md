# PS 26165 — Backend API Specification
### Everything the backend developer needs to start building, in one doc

This maps 1:1 onto: the Postgres schema and pipeline stages already defined for the AI/ML side, and the 6 dashboard screens already defined for the frontend. Every endpoint below states which DB table(s) it reads/writes and which frontend screen(s) consume it, so nothing is built speculatively.

---

## 0. Conventions

- **Base URL:** `/api/v1`
- **Auth:** Bearer JWT in `Authorization` header. Roles: `hse_reviewer`, `hse_manager`, `auditor`. (MVP: hardcoded role per demo login is fine — see Section 9.)
- **Content type:** `application/json` for all requests/responses except `POST /reports/ingest`, which accepts `multipart/form-data` (CSV upload) or `application/json` (array body).
- **Pagination:** all list endpoints accept `?limit=` (default 50, max 200) and `?offset=` (default 0), and return:
```json
{ "items": [...], "total": 342, "limit": 50, "offset": 0 }
```
- **Standard error envelope** (all non-2xx responses):
```json
{ "error": { "code": "REPORT_NOT_FOUND", "message": "No report with id abc123", "status": 404 } }
```
- **Timestamps:** ISO-8601 UTC (`"2026-09-05T10:26:00Z"`) everywhere.
- **IDs:** all entity IDs are strings (8-char UUID fragments, matching the AI/ML side's `report_id` format already in use — don't switch to auto-increment ints, it'll break the join between the two teams' work).

---

## 1. Ingestion

### `POST /reports/ingest`
Batch-load reports into the system (from a CSV export or the synthetic dataset). Triggers the async pipeline (Stage 0 → Stage 4) for every report ingested — does NOT block waiting for classification to finish.

**Request (CSV upload):** `multipart/form-data`, field `file`, containing columns matching `synthetic_uauc_reports.csv`: `report_id, site, report_text, source` (minimum required: `site`, `report_text`; `report_id` auto-generated if absent).

**Request (JSON array, alternative):**
```json
{
  "reports": [
    { "site": "Rig 4", "report_text": "During hot work near PMCC...", "source": "synthetic" }
  ]
}
```

**Response `202 Accepted`:**
```json
{ "ingested_count": 340, "batch_id": "batch_9f2e1a", "status": "processing" }
```

**Roles:** `hse_manager` only.
**DB:** inserts into `reports`; kicks off the pipeline which populates `extracted_fields` and `classifications` asynchronously.
**Notes:** `source` must be `"synthetic"` or `"real"` — never leave it null. The frontend's synthetic-data banner (Frontend Section 3.4) reads this field directly, so getting it wrong breaks that guardrail.

### `GET /reports/ingest/{batch_id}/status`
Poll ingestion/classification progress for a batch (needed because Stage 1 extraction is not instant).

**Response `200`:**
```json
{ "batch_id": "batch_9f2e1a", "total": 340, "classified": 340, "status": "complete" }
```
**Roles:** `hse_manager`, `hse_reviewer`.

---

## 2. Reports

### `GET /reports`
List reports with filters — powers any "browse all reports" table view.

**Query params:** `site`, `sif_potential` (bool), `bucket` (enum, see Section 4), `lsr_tag`, `date_from`, `date_to`, `source` (synthetic/real).

**Response `200`:**
```json
{
  "items": [
    { "report_id": "a1b2c3d4", "site": "Rig 4", "timestamp": "2026-08-20T09:00:00Z",
      "sif_potential": true, "bucket": "HIGH_CONF_SIF", "lsr_tag": "Energy Isolation" }
  ],
  "total": 340, "limit": 50, "offset": 0
}
```
**DB:** `reports` JOIN `classifications`.

### `GET /reports/{report_id}`
**The single most important endpoint — powers the Report Detail View screen.** Returns everything needed to render highlighted spans + justification + LSR tag in one call (no N+1 fetching from the frontend).

**Response `200`:**
```json
{
  "report_id": "a1b2c3d4",
  "site": "Rig 4",
  "timestamp": "2026-08-20T09:00:00Z",
  "source": "synthetic",
  "report_text": "During maintenance on process equipment at Rig 4, a worker was standing within the immediate hazard zone. Isolation status was not clearly confirmed by the crew. No injury occurred.",
  "extracted_fields": {
    "activity": { "text": "maintenance on process equipment", "span": [7, 40], "confidence": 0.91 },
    "energy_type": { "label": "stored/electrical energy", "confidence": 0.86 },
    "barrier_status": { "label": "uncertain", "span": [98, 145], "confidence": 0.79 },
    "exposure": { "label": "direct_proximity", "span": [55, 96], "confidence": 0.88 }
  },
  "classification": {
    "sif_potential": true,
    "confidence": 0.91,
    "bucket": "HIGH_CONF_SIF",
    "lsr_tag": "Energy Isolation",
    "justification": "Flagged as SIF-potential: stored/electrical energy present, isolation status uncertain, worker in direct proximity.",
    "model_version": "baseline2-v0.3"
  },
  "review_status": "pending"
}
```
**DB:** `reports` + `extracted_fields` + `classifications`.
**Notes:** `span` is `[start_char, end_char]` into `report_text` — this is exactly what the frontend's `<mark>`-based highlighting component (Frontend Section 3.2) needs; do not return extracted text without spans, highlighting can't be built from that alone.

---

## 3. Dashboard

### `GET /dashboard/rankings`
Powers the Site/Activity Ranking screen.

**Query params:** `metric` = `simple` | `composite` (default `simple` — per the metric-toggle requirement), `group_by` = `site` | `activity` (default `site`), `window_days` (default 42 / 6 weeks).

**Response `200`:**
```json
{
  "metric": "simple",
  "window_days": 42,
  "rankings": [
    { "group": "Rig 4", "sif_flagged_count": 18, "total_reports": 98, "density": 0.184,
      "trend_direction": "up", "trend_pct": 45.0, "primary_lsr": "Energy Isolation" },
    { "group": "Plant C", "sif_flagged_count": 3, "total_reports": 71, "density": 0.042,
      "trend_direction": "flat", "trend_pct": 2.0, "primary_lsr": "Confined Space" }
  ]
}
```
**DB:** aggregation query over `reports` + `classifications`, grouped by site/activity.
**Notes:** when `metric=composite`, response additionally includes a `"weights"` object showing the (currently equal, tunable) weights used — this is the "toggle shows methodological honesty" requirement from the frontend spec; never silently compute composite without exposing the weights.

### `GET /dashboard/clusters`
Powers the Precursor Cluster/Graph View.

**Query params:** `site` (optional filter), `min_cluster_size` (default 3).

**Response `200`:**
```json
{
  "clusters": [
    {
      "cluster_id": "c17",
      "pattern_summary": "Maintenance + stored energy + unverified isolation + direct exposure",
      "member_report_ids": ["a1b2c3d4", "e5f6a7b8", "..."],
      "member_count": 18,
      "sites": ["Rig 4", "Rig 7", "Plant C"],
      "primary_lsr": "Energy Isolation",
      "pattern_type": "established"
    }
  ],
  "edges": [
    { "source": "a1b2c3d4", "target": "e5f6a7b8", "similarity": 0.87 }
  ]
}
```
**DB:** `precursor_clusters` table, populated by the batch clustering job (AI/ML Stage 4). `edges` computed on read from stored pairwise similarities, or precomputed and stored — implementer's call based on graph size.
**Notes:** `pattern_type` is one of `established` / `emerging` / `sporadic_high_severity` (per the recurring-vs-emerging distinction) — this drives the color coding on the frontend graph, don't omit it.

### `GET /dashboard/trends`
Powers the Trend/Early-Warning Chart.

**Query params:** `site`, `lsr_tag`, `granularity` = `weekly` | `monthly` (default `weekly`).

**Response `200`:**
```json
{
  "series": [
    { "period": "2026-08-03", "count": 4 },
    { "period": "2026-08-10", "count": 7 },
    { "period": "2026-08-17", "count": 15 }
  ],
  "alerts": [
    { "period": "2026-08-17", "message": "Unusual increase in reported precursor rate — investigate.", "method": "CUSUM" }
  ]
}
```
**DB:** aggregation over `classifications` + `precursor_clusters`.
**Notes:** the `message` field text is fixed copy, not model-generated per-alert text — this is deliberate (Section 12 of the research blueprint: never let the wording drift toward a causal/predictive claim). Backend should not let a future refactor make this field free-text from a model.

### `GET /dashboard/summary`
Powers the top-level "SIF Action Center" header (high-priority pattern count, overall stats) — a lightweight aggregate endpoint so the dashboard's landing view doesn't have to call 3 other endpoints just to render a header.

**Response `200`:**
```json
{
  "total_reports": 2184,
  "high_priority_pattern_count": 7,
  "reports_pending_review": 95,
  "last_ingested_at": "2026-09-05T06:00:00Z"
}
```

---

## 4. Review Queue (Human-in-the-Loop)

### `GET /review-queue`
Powers the HSE Review Queue screen. Returns reports in `LOW_CONF_REVIEW` bucket, oldest-first by default.

**Query params:** `site`, `sort` = `oldest` | `newest` | `confidence_asc`.

**Response `200`:** same shape as `GET /reports` list, filtered to `bucket=LOW_CONF_REVIEW` plus `bucket=NEEDS_MORE_INFO`.

### `POST /review-queue/{report_id}/action`
Reviewer confirms/corrects/rejects a classification.

**Request:**
```json
{
  "action": "correct",
  "corrected_sif_potential": false,
  "corrected_lsr_tag": null,
  "reviewer_notes": "Isolation was in fact verified per follow-up call to site."
}
```
`action` is one of: `confirm` | `correct` | `reject`.

**Response `200`:**
```json
{ "report_id": "a1b2c3d4", "review_action_id": "rv_4471", "status": "recorded",
  "promoted_to_training_queue": false }
```

**DB:** inserts into `review_actions`; updates `reports.review_status`. `promoted_to_training_queue` becomes `true` only once **2 independent reviewers** have recorded the same corrected label for that report (the 2-reviewer-agreement gate from the AI/ML spec) — this logic lives in the backend, not the AI/ML pipeline, since it's a workflow/database concern (checking for a second matching `review_actions` row), not a model concern.
**Roles:** `hse_reviewer`, `hse_manager`.

---

## 5. Recommendations / Intervention Engine

### `GET /recommendations`
Powers the "SIF Action Center" list of high-priority patterns with recommended actions (the novelty/intervention layer).

**Response `200`:**
```json
{
  "recommendations": [
    {
      "pattern_id": "c17",
      "title": "Energy Isolation Failure",
      "evidence_summary": { "report_count": 18, "site_count": 4, "window_days": 42, "trend_pct": 45.0 },
      "primary_barrier_failure": "Isolation verification",
      "priority": "HIGH"
    }
  ]
}
```
**DB:** joins `precursor_clusters` with intervention-library lookups (AI/ML `recommendation/intervention_library.py`) — backend calls this via the AI/ML inference API (Section 7), it does not reimplement the lookup logic itself.

### `GET /recommendations/{pattern_id}`
Full detail view — "evidence trail" click-through.

**Response `200`:**
```json
{
  "pattern_id": "c17",
  "title": "Energy Isolation Failure",
  "evidence": {
    "report_count": 18, "site_count": 4, "window_days": 42,
    "member_report_ids": ["a1b2c3d4", "..."],
    "breakdown": { "mentions_missing_isolation": 14, "involves_maintenance": 11, "involves_equipment_opening": 8 },
    "sites": ["Rig 4", "Rig 7", "Plant C", "Well Site B"]
  },
  "recommended_interventions": [
    { "rank": 1, "control_level": "administrative", "priority": "HIGH",
      "action": "Mandatory isolation verification checkpoint" },
    { "rank": 2, "control_level": "administrative", "priority": "HIGH",
      "action": "Supervisor PTW closure/start checkpoint" },
    { "rank": 3, "control_level": "training", "priority": "MEDIUM",
      "action": "Targeted Energy Isolation toolbox campaign" }
  ],
  "expected_objective": "Reduce recurrence of reports involving unverified energy isolation."
}
```
**Notes:** `expected_objective` wording must never claim a causal/predictive effect (per the intervention-simulator honesty requirement) — this is fixed template text assembled from the pattern's barrier type, not free-text generation.

### `POST /recommendations/{pattern_id}/action-plan`
HSE manager commits to an intervention — this is what the "CREATE ACTION PLAN" button calls, and is what makes outcome-tracking (below) possible.

**Request:**
```json
{ "selected_intervention_ranks": [1, 2], "target_sites": ["Rig 4"], "planned_start_date": "2026-09-15" }
```
**Response `201`:**
```json
{ "action_plan_id": "ap_2201", "pattern_id": "c17", "status": "planned" }
```
**Roles:** `hse_manager` only.
**DB:** new `action_plans` table (see Section 8 — additive to the schema already defined): `id, pattern_id, selected_interventions JSON, target_sites[], planned_start_date, actual_start_date, status, created_by, created_at`.

---

## 6. Intervention / Outcome Tracking

### `GET /action-plans/{action_plan_id}/impact`
Powers the "before/after" outcome-tracking chart.

**Response `200`:**
```json
{
  "action_plan_id": "ap_2201",
  "pattern_id": "c17",
  "intervention_start_date": "2026-09-15",
  "before": { "window_days": 42, "precursor_rate": 0.184 },
  "after_weekly": [
    { "week": 1, "precursor_rate": 0.179 },
    { "week": 2, "precursor_rate": 0.142 },
    { "week": 3, "precursor_rate": 0.108 }
  ],
  "pct_change": -41.3,
  "disclaimer": "Reported precursor frequency change following the intervention. Historical association only — not a causal claim."
}
```
**DB:** `action_plans` joined against `classifications`/`precursor_clusters` filtered to dates before/after `actual_start_date`.
**Notes:** `disclaimer` is a fixed string, always returned, never omitted — the frontend should render it adjacent to the chart, not as a tooltip someone has to hover to find.

### `PATCH /action-plans/{action_plan_id}`
Mark an action plan as actually started (vs. just planned) — needed because `planned_start_date` and `actual_start_date` can differ in reality.

**Request:** `{ "actual_start_date": "2026-09-18", "status": "in_progress" }`
**Response `200`:** updated action plan object.
**Roles:** `hse_manager`.

---

## 7. Internal: AI/ML Pipeline Bridge

These are not called by the frontend directly — they're how the Backend service invokes the AI/ML `sif_engine` package. Documented here because the backend dev is the one wiring them, even though they may end up as direct Python calls rather than HTTP if AI/ML runs in-process (see Backend Section 2.2 — sync call to a Python module is fine for MVP, no need for network hop). If AI/ML instead runs as its own service:

### `POST /internal/pipeline/run` (AI/ML service, called by Backend)
```json
{ "report_id": "a1b2c3d4", "report_text": "..." }
```
**Response:** the same `extracted_fields` + `classification` shape as `GET /reports/{id}` above — this is intentional, the backend endpoint is mostly a passthrough/persist wrapper around this.

### `POST /internal/pipeline/run-batch`
Same, batched — called after `POST /reports/ingest`.

**Decision for the backend dev:** for the 10-day MVP, implement `sif_engine` as an installed Python package (`pip install -e .` from the AI/ML repo) and call `sif_engine.pipeline.run_single()` / `run_batch()` directly as function calls inside the FastAPI request handler — do NOT stand up a second HTTP service for this. Only split it into a real internal API if/when the AI/ML models need independent scaling or a different runtime.

---

## 8. Audit & Admin

### `GET /audit-log`
**Query params:** `entity_type`, `entity_id`, `actor`, `date_from`, `date_to`.
**Response `200`:** paginated list of `{ id, entity_type, entity_id, action, actor, timestamp }`.
**Roles:** `auditor`, `hse_manager` only — `hse_reviewer` gets `403`.

### `GET /ontology`
Read-only exposure of `configs/ontology.yaml` (from the AI/ML repo) so the frontend can render human-readable labels (energy types, LSR names) without hardcoding them twice.
**Response `200`:** the parsed YAML as JSON.
**Roles:** any authenticated role.

### `GET /health`
**Response `200`:** `{ "status": "ok", "model_version": "baseline2-v0.3", "db": "connected" }` — no auth required, used for judge-facing "is the system alive" checks and for your own deployment sanity checks.

---

## 9. Auth (MVP-level, honestly scoped)

### `POST /auth/login`
**Request:** `{ "username": "hse_demo", "password": "..." }`
**Response `200`:** `{ "access_token": "...", "role": "hse_reviewer" }`
**Notes:** for the SIH demo, 3 hardcoded demo accounts (one per role) are entirely acceptable — do not over-invest in a real user-management system here; say so explicitly if a judge asks, per the "what should NOT be attempted" list from the build plan.

### `GET /auth/me`
**Response `200`:** `{ "username": "hse_demo", "role": "hse_reviewer" }`

---

## 10. Endpoint Summary Table (for sprint planning)

| Endpoint | Method | Screen(s) it powers | Priority |
|---|---|---|---|
| `/reports/ingest` | POST | (none directly — pipeline trigger) | **Day 1-2 — build first** |
| `/reports/ingest/{batch_id}/status` | GET | (loading state) | Day 2 |
| `/reports/{report_id}` | GET | Report Detail View | **Day 1-2 — build first, highest demo value** |
| `/reports` | GET | (generic list/search) | Day 3 |
| `/dashboard/rankings` | GET | Ranking Dashboard | Day 4 |
| `/dashboard/clusters` | GET | Cluster/Graph View | Day 5-6 |
| `/dashboard/trends` | GET | Trend Chart | Day 5 |
| `/dashboard/summary` | GET | Action Center header | Day 6 |
| `/review-queue` | GET | Review Queue | Day 4 |
| `/review-queue/{id}/action` | POST | Review Queue | Day 4 |
| `/recommendations` | GET | Action Center list | Day 6-7 |
| `/recommendations/{pattern_id}` | GET | Evidence trail detail | Day 6-7 |
| `/recommendations/{pattern_id}/action-plan` | POST | "Create Action Plan" button | Day 7-8 (stretch) |
| `/action-plans/{id}/impact` | GET | Before/after tracker | Day 8 (stretch) |
| `/audit-log` | GET | Auditor view | Day 8 |
| `/ontology` | GET | Label lookups everywhere | Day 3 |
| `/health` | GET | — | Day 1 |
| `/auth/login`, `/auth/me` | POST/GET | Login screen | Day 3 |

Build top-to-bottom by priority column — everything below "Day 6-7" is explicitly stretch scope per the 10-day build plan, and the demo still works without it (recommendations/action-plans can be shown as static/mocked screens if time runs out, per the frontend spec's own mocking allowance).
