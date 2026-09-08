/**
 * Offline fixture dispatcher for NEXT_PUBLIC_USE_MOCKS mode.
 * Maps `${method} ${path}` to fixture data (or a simulated ApiError) so the
 * whole UI is demoable with no backend / Postgres running.
 */
import { ApiError } from "../errors";
import {
  REPORT_FIXTURES,
  REPORT_LIST_ORDER,
  REVIEW_QUEUE_BUCKETS,
  PROMOTES_ON_ACTION,
} from "./reports";
import {
  RANKINGS_BY_SITE,
  RANKINGS_BY_ACTIVITY,
  METRIC_WEIGHTS,
  CLUSTERS,
  CLUSTER_EDGES,
  trendSeries,
  DASHBOARD_SUMMARY,
} from "./dashboard";
import {
  RECOMMENDATION_LIST,
  RECOMMENDATION_DETAIL,
  ACTION_PLANS,
  impactFor,
  type StoredPlan,
} from "./recommendations";
import { AUDIT_LOG } from "./audit";

/**
 * In-memory record of reports actioned during this browser session, so a
 * reviewed report drops out of subsequent GET /review-queue responses —
 * mirroring the backend flipping reports.review_status away from "pending".
 */
const reviewedThisSession = new Set<string>();

interface MockCall {
  method: string;
  query?: Record<string, string | number | boolean | undefined | null>;
  body?: unknown;
}

const DEMO_USERS: Record<string, { role: string }> = {
  hse_demo: { role: "hse_reviewer" },
  manager_demo: { role: "hse_manager" },
  auditor_demo: { role: "auditor" },
  reviewer_2: { role: "hse_reviewer" },
};

export async function resolveMock(path: string, call: MockCall): Promise<unknown> {
  await delay(140 + Math.random() * 220);
  const key = `${call.method} ${path}`;

  // --- auth -------------------------------------------------------------
  if (key === "POST /auth/login") {
    const { username, password } = (call.body ?? {}) as {
      username?: string;
      password?: string;
    };
    const u = username ? DEMO_USERS[username] : undefined;
    if (!u || password !== "demo123") {
      throw new ApiError({
        code: "INVALID_CREDENTIALS",
        message: "Invalid username or password",
        status: 401,
      });
    }
    return { access_token: `mock.${username}.${Date.now()}`, role: u.role };
  }

  if (key === "GET /auth/me") {
    return { username: "manager_demo", role: "hse_manager" };
  }

  // --- report detail --------------------------------------------------
  const detail = path.match(/^\/reports\/([^/]+)$/);
  if (detail && call.method === "GET") {
    const id = decodeURIComponent(detail[1]);

    // Reproduce the live backend 500 on hazard-shape mismatch.
    if (id === "r-4499" || call.query?.simulate === "500") {
      throw new ApiError({
        code: "SERVER_ERROR",
        message:
          "500: ValidationError — ExtractedSpanField requires 'text'; pipeline hazard field supplied {best_category, matches}.",
        status: 500,
      });
    }

    const fixture = REPORT_FIXTURES[id];
    if (!fixture) {
      throw new ApiError({
        code: "REPORT_NOT_FOUND",
        message: `No report with id ${id}`,
        status: 404,
      });
    }
    return fixture;
  }

  // --- reports list -------------------------------------------------
  if (path === "/reports" && call.method === "GET") {
    const q = call.query ?? {};
    let ids = [...REPORT_LIST_ORDER];
    if (q.source) {
      ids = ids.filter((i) => REPORT_FIXTURES[i].source === q.source);
    }
    if (q.bucket) {
      ids = ids.filter(
        (i) => REPORT_FIXTURES[i].classification.bucket === q.bucket
      );
    }
    if (q.site) {
      ids = ids.filter((i) => REPORT_FIXTURES[i].site === q.site);
    }
    if (q.lsr_tag) {
      ids = ids.filter(
        (i) => REPORT_FIXTURES[i].classification.lsr_tag === q.lsr_tag
      );
    }
    if (q.sif_potential !== undefined && q.sif_potential !== null) {
      const want = String(q.sif_potential) === "true";
      ids = ids.filter(
        (i) => REPORT_FIXTURES[i].classification.sif_potential === want
      );
    }
    if (q.date_from) {
      ids = ids.filter(
        (i) => REPORT_FIXTURES[i].timestamp >= String(q.date_from)
      );
    }
    if (q.date_to) {
      ids = ids.filter(
        (i) => REPORT_FIXTURES[i].timestamp.slice(0, 10) <= String(q.date_to)
      );
    }
    const items = ids.map((i) => {
      const r = REPORT_FIXTURES[i];
      return {
        report_id: r.report_id,
        site: r.site,
        timestamp: r.timestamp,
        sif_potential: r.classification.sif_potential,
        bucket: r.classification.bucket,
        lsr_tag: r.classification.lsr_tag,
      };
    });
    return { items, total: items.length, limit: 50, offset: 0 };
  }

  // --- review queue ------------------------------------------------
  if (path === "/review-queue" && call.method === "GET") {
    const q = call.query ?? {};
    let rows = Object.values(REPORT_FIXTURES).filter(
      (r) =>
        REVIEW_QUEUE_BUCKETS.includes(r.classification.bucket) &&
        r.review_status === "pending" &&
        !reviewedThisSession.has(r.report_id)
    );
    if (q.site) rows = rows.filter((r) => r.site === q.site);

    const sort = String(q.sort ?? "oldest");
    rows.sort((a, b) => {
      if (sort === "confidence_asc") {
        return a.classification.confidence - b.classification.confidence;
      }
      const t = +new Date(a.timestamp) - +new Date(b.timestamp);
      return sort === "newest" ? -t : t;
    });

    const items = rows.map((r) => ({
      report_id: r.report_id,
      site: r.site,
      timestamp: r.timestamp,
      sif_potential: r.classification.sif_potential,
      bucket: r.classification.bucket,
      lsr_tag: r.classification.lsr_tag,
    }));
    return { items, total: items.length, limit: 50, offset: 0 };
  }

  const action = path.match(/^\/review-queue\/([^/]+)\/action$/);
  if (action && call.method === "POST") {
    const id = decodeURIComponent(action[1]);
    const body = (call.body ?? {}) as {
      action?: string;
      corrected_sif_potential?: boolean | null;
      corrected_lsr_tag?: string | null;
      reviewer_notes?: string | null;
    };

    if (!REPORT_FIXTURES[id]) {
      throw new ApiError({
        code: "REPORT_NOT_FOUND",
        message: `No report with id ${id}`,
        status: 404,
      });
    }
    if (!["confirm", "correct", "reject"].includes(String(body.action))) {
      throw new ApiError({
        code: "VALIDATION_ERROR",
        message: "action must be one of confirm | correct | reject",
        status: 422,
      });
    }
    if (
      body.action === "correct" &&
      (body.corrected_sif_potential === undefined ||
        body.corrected_sif_potential === null)
    ) {
      throw new ApiError({
        code: "VALIDATION_ERROR",
        message: "corrected_sif_potential is required when action='correct'",
        status: 422,
      });
    }
    if (reviewedThisSession.has(id)) {
      throw new ApiError({
        code: "DUPLICATE_REVIEW",
        message: "You have already recorded an action for this report.",
        status: 400,
      });
    }

    reviewedThisSession.add(id);
    return {
      report_id: id,
      review_action_id: `rv_${Math.random().toString(36).slice(2, 8)}`,
      status: "recorded",
      promoted_to_training_queue: PROMOTES_ON_ACTION.has(id),
    };
  }

  // --- dashboard: rankings ---------------------------------------------
  if (path === "/dashboard/rankings" && call.method === "GET") {
    const q = call.query ?? {};
    const groupBy = String(q.group_by ?? "site");
    const metric = String(q.metric ?? "simple");
    return {
      metric,
      window_days: Number(q.window_days ?? 42),
      rankings: groupBy === "activity" ? RANKINGS_BY_ACTIVITY : RANKINGS_BY_SITE,
      weights: metric === "composite" ? METRIC_WEIGHTS : null,
    };
  }

  // --- dashboard: clusters --------------------------------------------
  if (path === "/dashboard/clusters" && call.method === "GET") {
    const q = call.query ?? {};
    const minSize = Number(q.min_cluster_size ?? 3);
    let clusters = CLUSTERS.filter((c) => c.member_count >= minSize);
    if (q.site) {
      clusters = clusters.filter((c) => c.sites.includes(String(q.site)));
    }
    const ids = new Set(clusters.flatMap((c) => c.member_report_ids));
    const edges = CLUSTER_EDGES.filter(
      (e) => ids.has(e.source) && ids.has(e.target)
    );
    return { clusters, edges };
  }

  // --- dashboard: trends --------------------------------------------
  if (path === "/dashboard/trends" && call.method === "GET") {
    const q = call.query ?? {};
    return trendSeries(
      String(q.granularity ?? "weekly"),
      q.site ? String(q.site) : undefined,
      q.lsr_tag ? String(q.lsr_tag) : undefined
    );
  }

  // --- dashboard: summary -----------------------------------------
  if (path === "/dashboard/summary" && call.method === "GET") {
    return DASHBOARD_SUMMARY;
  }

  // --- recommendations -----------------------------------------------
  if (path === "/recommendations" && call.method === "GET") {
    return { recommendations: RECOMMENDATION_LIST };
  }

  const recDetail = path.match(/^\/recommendations\/([^/]+)$/);
  if (recDetail && call.method === "GET") {
    const pid = decodeURIComponent(recDetail[1]);
    const d = RECOMMENDATION_DETAIL[pid] ?? RECOMMENDATION_DETAIL.c17;
    return d;
  }

  const recPlan = path.match(/^\/recommendations\/([^/]+)\/action-plan$/);
  if (recPlan && call.method === "POST") {
    const pid = decodeURIComponent(recPlan[1]);
    const body = (call.body ?? {}) as {
      selected_intervention_ranks?: number[];
      target_sites?: string[];
      planned_start_date?: string;
    };
    if (
      !Array.isArray(body.selected_intervention_ranks) ||
      body.selected_intervention_ranks.length === 0
    ) {
      throw new ApiError({
        code: "VALIDATION_ERROR",
        message: "Select at least one intervention.",
        status: 422,
      });
    }
    const id = `ap_${Math.random().toString(36).slice(2, 8)}`;
    const plan: StoredPlan = {
      action_plan_id: id,
      pattern_id: pid,
      selected_intervention_ranks: body.selected_intervention_ranks,
      target_sites: body.target_sites ?? [],
      planned_start_date: body.planned_start_date ?? "",
      status: "planned",
    };
    ACTION_PLANS[id] = plan;
    return { action_plan_id: id, pattern_id: pid, status: "planned" };
  }

  const planPatch = path.match(/^\/action-plans\/([^/]+)$/);
  if (planPatch && call.method === "PATCH") {
    const id = decodeURIComponent(planPatch[1]);
    const plan = ACTION_PLANS[id];
    if (!plan) {
      throw new ApiError({
        code: "PLAN_NOT_FOUND",
        message: `Action plan '${id}' not found`,
        status: 404,
      });
    }
    const body = (call.body ?? {}) as {
      actual_start_date?: string | null;
      status?: string | null;
    };
    if (body.actual_start_date) plan.actual_start_date = body.actual_start_date;
    if (body.status) plan.status = body.status;
    return {
      action_plan_id: plan.action_plan_id,
      pattern_id: plan.pattern_id,
      status: plan.status,
    };
  }

  const planImpact = path.match(/^\/action-plans\/([^/]+)\/impact$/);
  if (planImpact && call.method === "GET") {
    return impactFor(decodeURIComponent(planImpact[1]));
  }

  // --- audit log ----------------------------------------------------
  if (path === "/audit-log" && call.method === "GET") {
    const q = call.query ?? {};
    let rows = [...AUDIT_LOG];
    if (q.entity_type)
      rows = rows.filter((r) => r.entity_type === String(q.entity_type));
    if (q.entity_id)
      rows = rows.filter((r) => r.entity_id === String(q.entity_id));
    if (q.actor) rows = rows.filter((r) => r.actor === String(q.actor));
    if (q.date_from)
      rows = rows.filter((r) => r.timestamp >= String(q.date_from));
    if (q.date_to) rows = rows.filter((r) => r.timestamp <= String(q.date_to));
    return { items: rows, total: rows.length, limit: 50, offset: 0 };
  }

  throw new ApiError({
    code: "MOCK_NOT_IMPLEMENTED",
    message: `No offline fixture for ${key}. This screen lands in a later build pass.`,
    status: 501,
  });
}

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}
