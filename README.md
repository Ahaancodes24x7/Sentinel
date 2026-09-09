# Sentinel — AI/NLP Engine for SIF-Precursor Detection

**SIH 2026 · PS 26165 · Oil India Limited · Smart Automation**

Given a free-text HSSE observation, infer whether the situation described carried
**credible fatal potential — independent of what actually happened** — and explain
that inference in the terms an HSE engineer already uses.

That framing is the whole problem. A dropped wrench that lands 30 cm from a boot is
a "no injury" event by outcome and a live high-energy precursor by exposure. A
sprained wrist on a wet floor is a real injury and usually not a precursor. Any
model trained on "did this look like a bad past incident" systematically misses
exactly the reports the problem statement asks us to surface.

---

## What is actually built

| Layer | Status |
|---|---|
| Synthetic corpus generator (25k reports, gold NER spans, planted patterns) | Built |
| Stage 0 preprocessing (abbreviations, code-mix, typos) | Built |
| Stage 1 extraction (activity / energy / barrier / exposure / location) | Built — rules + fine-tuned DistilBERT NER |
| Stage 2 SCL reasoning (energy → barrier → exposure → consequence → LSR) | Built — fixed, auditable decision structure |
| Stage 3 calibrated confidence + 4-bucket routing | Built |
| Stage 4 pattern discovery (HDBSCAN, association mining, CUSUM/EWMA) | Built |
| Intervention engine (curated control library, hierarchy of controls) | Built |
| FastAPI backend + PostgreSQL, 30 endpoints | Built |
| React console, 14 screens, all on live API data | Built |

**Not built, deliberately:** OIL system integration, real-time streaming ingestion,
production user management, human/organisational-factor causal inference. Each is
called out in the honesty section below rather than faked.

---

## Quick start

### 1. Install

```bash
python -m pip install -r requirements.txt
python -m pip install -r aiml/requirements.txt
cd frontend && npm install && cd ..
```

### 2. PostgreSQL

The backend requires PostgreSQL in normal operation and refuses to fall back to
SQLite silently — a demo that quietly runs on a different database than the one
you describe is a credibility risk.

```powershell
# Windows (winget)
winget install PostgreSQL.PostgreSQL.16
```

Then create the database and export the connection string:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\createdb.exe" -U postgres sentinel_db
$env:DATABASE_URL = "postgresql://postgres:<your-password>@localhost:5432/sentinel_db"
```

```bash
# bash / git-bash
export DATABASE_URL="postgresql://postgres:<your-password>@localhost:5432/sentinel_db"
```

> **Running the test suite only?** `TEST_ISOLATED_SQLITE=1` enables an in-memory
> SQLite database for tests. It is intentionally gated behind that explicit flag so
> it can never be the accidental default.

### 3. Generate data, train, seed

```bash
cd aiml
python scripts/generate_synthetic_data.py --n 25000    # corpus + dataset card
python scripts/train_models.py                          # baselines + calibration + eval report
python scripts/train_ner.py --samples 9000 --epochs 2   # DistilBERT NER (~50 min CPU)
python scripts/probe_ner_ood.py                         # honest generalisation probe
cd ..

python -m backend.seed_database --reset                 # runs the real pipeline over the corpus
```

`seed_database` pushes every report through the same Stage 0–3 code path the live
ingest endpoint uses — nothing is pre-baked — then runs the batch clustering job.
Full 25k takes roughly 15 minutes at ~25 reports/s; pass `--limit 6000` for a
faster demo dataset.

### 4. Run

**One port, everything served together** (what you share):

```bash
cd frontend && npm run build && cd ..
uvicorn backend.main:app --port 8000
```

Console at `http://localhost:8000`, API docs at `/docs`. The API process serves
the built console as well as the JSON, so it is a single origin — the frontend
calls a relative `/api/v1` and resolves against whatever host it is reached on.

**Two ports, with hot reload** (what you develop against):

```bash
uvicorn backend.main:app --reload --port 8000
cd frontend && npm run dev                        # console on :3000, proxies /api to :8000
```

Demo accounts (hardcoded, deliberately): `manager_demo` / `hse_demo` /
`auditor_demo`, all with password `demo123`.

### 5. Share it with someone

```powershell
devtunnel user login     # once per machine, opens a browser
.\share.ps1              # builds, starts, and prints a public https link
```

`share.ps1` tunnels the single port with anonymous access. Because the client
uses relative URLs, the shared link works with no rebuild and no CORS setup.

> **Before you share:** anonymous access means the link *is* the credential —
> the three demo logins are hardcoded, and a manager login can ingest reports and
> trigger the clustering job. The data behind it is the synthetic corpus, not
> real OIL data. Stop the tunnel with Ctrl+C when you are done.

---

## Architecture

```
Raw report text
  → Stage 0  preprocessing: abbreviation expansion, code-mix normalisation, typo repair
  → Stage 1  extraction: NER spans + ontology-constrained energy/barrier classifiers
  → Stage 2  SCL reasoning over the STRUCTURED FRAME, not the raw text
  → Stage 3  evidence-strength confidence → 4-bucket routing
  → Postgres event store (structured frame denormalised for querying)
  → Stage 4  batch clustering + association mining + control charts
  → FastAPI  → React console
```

The architectural decision that matters: **the raw text is never classified
directly**. Extraction is learned and fallible; the reasoning is a small fixed
decision structure any HSE engineer can read line by line, and it never needs
retraining. When extraction is weak the system routes to a human instead of
guessing.

---

## The five things a judge should remember

1. **Outcome-independent labelling.** The ground truth follows the EEI SCL model —
   high energy present, exposure occurred, no *direct* control confirmed — and never
   consults the stated outcome. A confirmed *administrative* control (a permit) does
   not clear a high-energy exposure the way an *engineering* one does.

2. **Evidence, not a score.** Every flagged report shows the character spans that
   drove the decision, highlighted in the source text, plus the reasoning chain and
   an ontology-grounded justification. Never a bare "SIF-potential: 87%".

3. **Patterns over structure, not vocabulary.** Clustering runs on the extracted
   event frame, so "stood under the load" and "was positioned beneath the suspended
   pipe section" land in the same pattern.

4. **Early warning that does not overclaim.** CUSUM and EWMA control charts against
   a rolling baseline, with fixed alert copy that says *"unusual increase in reported
   precursor rate — investigate"*. Never a fatality prediction.

5. **Recall-first routing.** The operating threshold is chosen on validation as the
   highest one still achieving the required recall, because a missed precursor is
   categorically worse than an extra human review — and the review-queue cost of that
   choice is stated, not hidden.

---

## Honesty section

Things this prototype does **not** do, stated up front:

- **It is not connected to OIL systems.** Ingestion is from CSV/JSON. There is no
  evidence of an accessible HSSE API in the problem statement, so none is claimed.
- **The corpus is synthetic and labelled as such** on every screen. The banner is
  permanent and non-dismissible.
- **It does not predict fatalities.** The temporal layer detects a change in
  *reporting rate* against a baseline. That is a different claim, and the UI copy
  says so next to the chart.
- **Metrics are internal consistency validation, not production validation.** The
  test split shares generation assumptions with the training split. The NER model
  scores span F1 = 1.000 on held-out synthetic data, which measures the generator's
  predictability rather than the model's quality — see
  `aiml/reports/ner_ood_probe.md` for the out-of-distribution probe that says
  something real.
- **The composite density metric is uncalibrated.** Weights default to equal, are
  shown in the API response and on screen, and are labelled `UNCALIBRATED`.
- **Findings are correlational.** Association rules state co-occurrence with an
  explicit baseline and lift. No causal language appears in any output.

Real validation requires an SME-reviewed gold set drawn from actual OIL exports,
with inter-annotator agreement measured (Cohen's κ > 0.6) before any threshold is
agreed as an acceptance criterion.

---

## Repository layout

```
aiml/
  configs/ontology.yaml         single shared taxonomy (energy, barriers, LSRs, sites)
  src/sif_engine/
    data_generation/            synthetic corpus generator with gold spans
    preprocessing/              Stage 0
    extraction/                 Stage 1 — NER, energy, barrier, embeddings
    reasoning/                  Stage 2 — SCL decision logic, consistency, consequence
    confidence/                 Stage 3 — calibration, evidence strength, routing
    patterns/                   Stage 4 — clustering, association mining, SPC
    recommendation/             curated intervention library + evidence trail
    site_intelligence/          site registry and analytics
  scripts/                      generate / train / probe / evaluate entry points
  reports/                      evaluation report, metrics.json, OOD probe
backend/
  main.py                       FastAPI app, 30 endpoints
  database.py                   SQLAlchemy models (PostgreSQL)
  analytics.py                  DB rows → event frames → patterns and metrics
  seed_database.py              corpus → pipeline → DB → clustering
frontend/
  src/api/                      typed client + React Query hooks (no mock fallback)
  src/components/kinetic/       motion primitives
  src/pages/                    14 screens
```

## Testing

```bash
TEST_ISOLATED_SQLITE=1 DATABASE_URL="sqlite:///:memory:" python -m pytest backend/tests -q
cd aiml && python -m pytest tests -q
```
