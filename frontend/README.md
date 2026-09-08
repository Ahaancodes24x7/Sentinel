# Sentinel Frontend

Next.js (App Router) + TypeScript + Tailwind console for the SIF-precursor
detection system (SIH PS 26165). Talks to the FastAPI backend under
`/api/v1` (see `../SIH_26165_Backend_API_Specification.md`).

## Status

| Delivered | Notes |
|---|---|
| Design system | Palette + type + panel/meter/chip primitives (`app/globals.css`, `components/ui/`) |
| Typed API client | `lib/api/` — fetch wrapper, Zod schemas mirroring `backend/schemas.py`, typed `ApiError` |
| Offline demo mode | `NEXT_PUBLIC_USE_MOCKS=true` serves fixtures from `lib/api/mocks/` — no backend/Postgres needed |
| Login | `/login` — 3 demo accounts, role stored client-side |
| Report Detail View | `/reports/[reportId]` — real span-highlight renderer, classification panel, per-field confidence, graceful handling of the known hazard-shape 500 |
| Reports list | `/reports` — basic list (full filterable browse is a later pass) |
| Review Queue | `/review-queue` — `LOW_CONF_REVIEW` + `NEEDS_MORE_INFO`, site/sort controls, expandable rows with justification + spans, per-report confirm/correct/reject form (corrected LSR tag must be chosen, no silent default), 2-reviewer promotion state, "queue clear" empty state. Role-gated to reviewer + manager |
| Rankings | `/rankings` — `GET /dashboard/rankings`, simple/composite + site/activity toggles, hand-rolled SVG density bars, trend chips on the semantic ramp. Composite mode renders the `weights` object in an open disclosure |
| Clusters | `/clusters` — `GET /dashboard/clusters`, hand-rolled SVG node-link graph (deterministic radial layout), cluster nodes sized by member count and coloured by `pattern_type` (3 distinct treatments), member-report edges by similarity, click-through to Report Detail |
| Trends | `/trends` — `GET /dashboard/trends`, hand-rolled SVG area/line chart, CUSUM alert markers; alert `message`/`method` rendered verbatim beside the chart |
| SIF Action Center | `/action-center` — summary header + recommendations list + detail (evidence trail, ranked interventions, verbatim `expected_objective`) + Create Action Plan (manager only) + `PATCH` mark-started + before/after impact chart with the `disclaimer` verbatim adjacent |
| Audit log | `/audit-log` — filterable, timestamp-sortable dense table. Role-gated to auditor + manager |

Reports browse filters (site/bucket/LSR/date/source) remain a follow-up — `/reports` is still a basic list.

## Run

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000
```

`.env.local` ships with `NEXT_PUBLIC_USE_MOCKS=true` so it runs with no backend.
To use the live API:

```bash
# .env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_USE_MOCKS=false
```

Demo accounts (password `demo123`): `manager_demo`, `hse_demo`, `auditor_demo`.

Mock report ids: `r-4401` (clean HIGH_CONF_SIF, overlapping spans), `r-4402`
(HIGH_CONF_NON_SIF), `r-4403`/`r-4404`/`r-4410`–`r-4413` (review-queue: LOW_CONF_REVIEW
/ NEEDS_MORE_INFO), `r-4405` (Working at Height), `r-4406` (buggy hazard shape —
inline notice), `r-4499` (simulated 500). Actioning `r-4412` in the queue trips the
2-reviewer gate and returns `promoted_to_training_queue: true`.

Action Center: recommendation `c17` exposes a "View a sample tracked plan" button
(mock only) that opens the impact tracker for pre-seeded plan `ap_seed01` with 4
weeks of after-data. Newly created plans show the "no post-intervention weeks yet"
state. Mock fixtures live in `lib/api/mocks/{dashboard,recommendations,audit}.ts`.

## Checks

```bash
npm run typecheck   # tsc --noEmit
npm run lint
npm run build
```

## Notes

- Fonts: IBM Plex Sans/Mono, self-hosted via `next/font/local` (`app/fonts.ts`,
  woff2 in `app/fonts/`, latin subset from `@fontsource`). No external font/CDN
  fetch at build or runtime — works fully offline.
- `GET /reports/{id}` can 500 on the backend when a report has hazard evidence
  (pipeline emits `{best_category, matches}`, endpoint expects
  `{text, span, confidence}`). The client treats this as an expected failure and
  renders a specific error state, not a blank screen.
