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
| FastAPI backend + PostgreSQL, 30+ endpoints | Built |
| React console, 15 screens, all on live API data | Built |
| Camera Watch — CCTV fire / smoke / fall / roof-fall detection that files its own prioritised complaints | Built (see below) |

**Not built, deliberately:** OIL system integration, an authorized live OIL camera
feed, production user management, human/organisational-factor causal inference,
PPE detection (the pretrained detector this prototype ships does not recognize
PPE, so it does not claim to). Each is called out in the honesty section below
rather than faked.

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

## Camera Watch — CCTV hazard monitoring

Real-time computer-vision hazard monitoring, alongside the report-analysis
pipeline above — same backend, same database, same console. It answers a
different question than the NLP side: not "what does this written report imply",
but "what is this camera seeing right now, is it the start of a disaster, and
who needs to be told".

**A camera that only lights up a tile has not helped anyone.** So the defining
behaviour of this feature is that a detected hazard **files its own complaint**:
the event is written into a plain-language field report, run through the same
Stage 0–3 SIF pipeline as a report a person typed, given a response priority,
and pushed into the normal review queue. One camera sighting produces one real,
auditable, prioritised report — with no human in the loop at write time.

### What it detects

A COCO-pretrained YOLO model recognises people, vehicles and everyday objects.
It cannot see any of the things that actually precede a mine or field disaster —
none of them are COCO classes. So detection here is two layers, not one:

| Layer | Sees | Hazards raised |
|---|---|---|
| YOLO detector | people, vehicles, plant, loose objects | restricted-zone entry, lifting-zone entry, vehicle–person proximity |
| Scene analysers (`scene_analysis.py`) | how the *scene* is changing over time | fire, smoke, visibility loss, worker fall, worker down and immobile, falling object / roof fall, struck-by, sudden evacuation or crowding |

Each scene analyser is classical CV over a short rolling history per camera:

- **Fire** — flame-colour mask intersected with *churn*: how much the mask
  changes once its bulk translation is cancelled out. A static orange object
  (painted plant, sodium lamp) churns ~0; a moving tan one (a face, a hi-vis
  jacket) churns 0.03–0.09 after alignment; a live flame churns 0.3–0.6. The
  largest connected component must also account for a real share of the lit
  pixels, which is what rejects compression speckle on a rock face.
- **Smoke** — grey, moving and *blurrier than the rest of the frame*. Seeded
  from background-subtractor motion (not from greyness — underground, nearly
  every pixel is grey), closed to bridge the churning rim into the body of the
  plume, then each component gated on texture. Detected people and vehicles are
  cut out first, so a worker in a grey overall is not a plume.
- **Visibility loss** — scene edge energy against that camera's own rolling
  baseline. Catches a dust cloud, a gas release or a smoke layer without needing
  to know which it is, and without firing on a scene that was simply always
  low-contrast.
- **Fall / worker down** — tracked person boxes going from upright to horizontal
  with downward velocity, escalating to a man-down event if the person then
  stops moving.
- **Falling object / roof fall** — masses descending under gravity, from YOLO
  boxes where the object has a name and from motion blobs where it does not (a
  rock, a section of roof, a length of pipe). Escalates to **struck-by** when the
  mass reaches a person, with a deliberately lower speed bar for that case.

### Tuned to over-report, never to miss

The operating rule for this feature is explicit: **a false alarm is acceptable,
a missed disaster is not.** That shows up in concrete places, not just in prose —
low detector confidence threshold, weak-evidence events still raised (carrying a
low confidence and a hedged "possible …" reading), a lower descent threshold
when a person is underneath, and every hazard family on the auto-report list. If
complaint filing itself fails, the event is still recorded and carries the
reason — losing a sighting because the paperwork failed would be the worst
outcome available.

### Priority: the stronger of two independent assessments

The camera judges severity from pixels. The SIF text pipeline judges the written
complaint from language. **Priority is the maximum of the two, never the
average**, and the report records which one set it:

> Priority set by the camera assessment (critical severity, 85% detection
> confidence); the text pipeline alone would have routed this as P4.

That arithmetic exists to prevent one specific failure: a text classifier that
confidently reads a generated narrative as non-SIF must not be able to route a
detected fire to a routine log entry. P1 = immediate response, P2 = urgent
review, P3 = elevated, P4 = routine.

### Observation vs. inference, kept separate

Every event states what was literally seen ("A flickering flame-coloured source
was detected in the camera view") and, separately, the interpretation a human
still has to confirm ("Probable open flame / active fire…"). Generated reports
end with an explicit line saying they were machine-written and unconfirmed, and
are stored with `source = "vision"` so they are never mistaken for something a
person filed.

**PPE detection is not implemented.** The pretrained model cannot recognise
helmets or vests, and claiming otherwise would undermine the honesty the rest of
this project is built on. The rule layer is structured so a dedicated PPE model
could be added later without restructuring it.

**This is decision support, not autonomous safety control.** Nothing here stops
equipment, sounds a physical alarm, or acts without a human.

### Three real OIL India sites

The demo spans three real OIL India operational locations — Duliajan, Digboi and
Moran, Assam — with two demo cameras each (`DUL-C01/C02`, `DIG-C01/C02`,
`MOR-C01/C02`). **Only the site names and coordinates are real.** Camera IDs,
safety zones and every event are demo data generated live by this prototype —
never a claim of installed OIL India CCTV infrastructure or an authorised feed.

Zone membership is tested at a person's **ground point** (bottom-centre of the
box), not the box centre. Using the centre makes anyone standing in front of a
zone drawn on a far wall register as inside it, which is the single largest
source of false zone alarms in a naive implementation.

### Running it

```bash
pip install -r aiml/requirements.txt   # adds ultralytics, opencv-python, torch
```

The first run downloads the ~6 MB `yolov8n.pt` weights from Ultralytics' release
assets (cached under `aiml/models/vision/` — not committed, same policy as the
NER weights below), so it needs a one-time internet connection. The model is
loaded and warmed at API startup on a background thread, so the first live frame
does not pay for it. Then:

```bash
uvicorn backend.main:app --reload --port 8000
cd frontend && npm run dev
```

Open the console → **Camera Watch** in the sidebar → choose a source:

- **Upload Video** — any video file with the scene you want to test. Frames are
  read in the browser and analysed on the same path as a live camera.
- **Live Webcam** — grants camera permission and analyses the live feed. This is
  the one to use for the burning-paper demo: light a piece of paper in front of
  the lens and the fire index climbs, the flame is boxed, a critical event fires
  and a P1 complaint appears in the queue within about a second.
- **RTSP / NVR** — points the backend directly at an IP camera or NVR; frames
  are then read and analysed server-side.

Measured on CPU: ~40 ms per frame end to end, ~3 fps sustained through the
browser loop, fire raised **0.7 s after ignition** in the reference clip.

The console shows the live per-frame hazard indices, so an operator watches a
number climb *before* anything fires rather than only seeing the alarm
afterwards. Inference runs on CUDA automatically when available; the active
device is shown on the video panel and in `GET /api/v1/vision/status`.

Tuning without code changes: `SENTINEL_VISION_WEIGHTS`, `SENTINEL_VISION_CONF`
and `SENTINEL_VISION_IMGSZ`.

### API

```
GET  /api/v1/vision/cameras         camera + safety-zone config, optionally by site
POST /api/v1/vision/start           begin a camera session (resets per-camera analyser state)
POST /api/v1/vision/stop            end a camera session
POST /api/v1/vision/analyze-frame   one frame in → detections + hazard indices + new events
                                    (each carrying the complaint it just filed) out
GET  /api/v1/vision/status          live counts, hazard totals, reports filed, indices, device
GET  /api/v1/vision/events          persisted hazard events, filterable by site/camera/status
POST /api/v1/vision/events/{id}/acknowledge
GET  /api/v1/reports?source=vision  the complaints the cameras filed
```

`analyze-frame` is the core loop. The frontend chains each capture off the
previous response rather than using a fixed interval — with an interval, a frame
slower than the tick stacks the next request on top of it and the backlog only
grows. The backend independently enforces a minimum interval per camera, and
serialises model inference, because FastAPI runs sync endpoints in a thread pool
and an Ultralytics model is not safe to call re-entrantly.

Events and generated reports are persisted to PostgreSQL (`vision_events` and
`reports`) the same way everything else in Sentinel is — there is no separate app
or database for this feature. New columns on `vision_events` are applied by an
additive migration at startup, so an existing database upgrades in place.

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
    vision/                     Camera Watch — YOLO detector, scene analysers, hazard rules,
                                 frame-processing session manager, event schema
  scripts/                      generate / train / probe / evaluate entry points
  reports/                      evaluation report, metrics.json, OOD probe
  models/vision/                yolov8n.pt cache (gitignored, auto-downloaded)
backend/
  main.py                       FastAPI app, 30+ endpoints incl. /api/v1/vision/*
  database.py                   SQLAlchemy models (PostgreSQL), incl. VisionEventModel
  analytics.py                  DB rows → event frames → patterns and metrics
  seed_database.py              corpus → pipeline → DB → clustering
frontend/
  src/api/                      typed client + React Query hooks (no mock fallback)
  src/components/kinetic/       motion primitives
  src/lib/siteContext.tsx       global 3-site selector (Duliajan/Digboi/Moran)
  src/pages/                    15 screens, incl. LiveVisionPage.tsx (Camera Watch)
```

## Testing

```bash
TEST_ISOLATED_SQLITE=1 DATABASE_URL="sqlite:///:memory:" python -m pytest backend/tests -q
cd aiml && python -m pytest tests -q
```

Camera Watch is covered by three files:

- `aiml/tests/test_vision.py` — detector wrapper, zone and proximity rules,
  event schema, the three-site camera registry.
- `aiml/tests/test_vision_scene.py` — the scene analysers and the complaint
  chain. Every detector is tested against its own worst case as well as its
  happy path: a flickering flame **and** a static orange object, a diffuse plume
  **and** a uniformly grey static scene, a fall **and** someone standing still,
  a mass falling onto a worker **and** flame churn that must not read as one.
  Temporal signals are exercised against a real clock, because a version of
  these tests that passed on a single frame would not be testing the thing that
  makes the detector work.
- `backend/tests/test_vision_api.py` — the API and database round trip, that a
  hazard event files a real prioritised report, and that the event survives a
  failure to file it.

The model-inference boundary (`YoloDetector.detect`) is mocked only in the
deterministic hazard-rule API tests — the scene analysers, the rule layer, the
complaint drafting, the priority arithmetic and the persistence path all run for
real.
