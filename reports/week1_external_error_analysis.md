# Week 1 External Error Analysis

**Corpus:** `data/external_eval/narratives.jsonl` (24 narratives, 19 public source
documents — Havtil, CSB, IADC; see `data/external_eval/README.md`).
**Gold labels:** `data/external_eval/annotations.jsonl`, single-annotator (this
session). **No inter-annotator agreement is available** — see status line below.
**Pipeline run:** `aiml/src/sif_engine/pipeline.run_single()`, HEAD `652780e`
plus the one Phase 7 fix described below, model = fine-tuned DistilBERT (live
default per `reports/week1_baseline.md` §1).

## Corpus composition caveat (read before the numbers)

22 of 24 gold labels are `sif_potential_gold = true` (1 `false`, 1 `UNKNOWN`).
This is a direct consequence of sourcing from regulator investigation reports
and industry safety alerts — organizations publish reports about incidents
that were serious or high-potential; they do not publish reports about
routine, uneventful shifts. **This corpus is therefore much better suited to
measuring recall/false-negative behavior than precision/false-positive
behavior.** The one deliberate negative case (`ext_005`, an environmental oil
spill with no personnel exposure) and the one deliberate `UNKNOWN` case
(`ext_023`, a lifeboat mechanical failure with no clear occupational-SIF
framing) were included specifically to probe false-positive risk and
boundary-case handling, not to make the set balanced. A Week 2 corpus
expansion should deliberately add negative/benign narratives (uneventful
inspections, near-misses that were fully controlled) to get a real precision
estimate — Week 1's precision number below should not be read as "Sentinel
has 100% precision on real text," only as "0 false positives were observed on
this small, positive-skewed sample."

## Headline result

| Metric (SCL-alone `sif_potential`, N=23 scoreable, 1 excluded for gold=UNKNOWN) | Before fix | After fix (Phase 7) |
|---|---|---|
| True positives | 3 | 11 |
| False negatives | 19 | 11 |
| False positives | 0 | 0 |
| True negatives | 1 | 1 |
| **Recall** | **0.136** | **0.500** |
| **Precision** | 1.000 | 1.000 |
| `HIGH_CONF_SIF` bucket ever assigned | 0 / 24 | 2 / 24 |

Compare against the synthetic held-out benchmark (`reports/week1_baseline.md`
§18): DistilBERT alone scores recall 0.962 on synthetic data. **The SCL
reasoner's recall on this external sample was 0.136 before any fix — a ~7x
drop versus its synthetic-domain behavior** (the SCL reasoner does not have
its own synthetic recall number reported anywhere in the repo prior to this
session, since it has never been benchmarked outside `run_single`'s own
pipeline; the B5 synthetic figure computed for this report, see below, was
0.844 recall / 0.715 precision on synthetic data, which puts the external
0.136 in context as still a severe, not merely incremental, drop). This is
exactly the generalization gap Week 1 was commissioned to find.

## Root cause (found, verified, reproducible)

Every extraction field in Sentinel's evidence extractor is phrase-list /
regex based (`reports/week1_baseline.md`, summary section). Tracing each of
the 19 false negatives individually (`data/external_eval/sentinel_outputs.jsonl`,
pre-fix copy preserved via the git-stash comparison below) showed the same
mechanism every time:

```
aiml/src/sif_engine/reasoning/scl_reasoner.py:145
    has_exposure = exposure_label in ["direct_proximity", "indirect_proximity"]
```

`has_exposure` is a hard gate in the core SIF decision (`scl_reasoner.py:163-180`,
quoted in `reports/week1_baseline.md` §12). It is **only** ever true if
`extract_exposure()` (`extraction/evidence_extractor.py:365`) matches one of the
phrases in `EXPOSURE_KEYWORD_GROUPS`. That list was built entirely from the
synthetic generator's own template vocabulary (prepositional/positional
phrases like "within the marked", "directly beneath", "worker was exposed
to") and contains **no phrase for the plain, common way a real narrative
states that someone was actually hit, pinned, crushed, trapped, or killed** —
"struck the deck operator", "pinned the floorman's left upper arm", "fatally
trapping the inspection team leader between the plates", "was overcome by
hydrogen sulfide gas". 21 of 24 external narratives came back `exposure:
unspecified` before the fix, even the ones describing fatalities.

By contrast, **`barrier_status = not_mentioned` did not block SIF detection**
— `has_barrier_gap` is already `True` for `not_mentioned` by design
(`scl_reasoner.py:112-131`, and `reports/week1_baseline.md` §12: "not_mentioned
is explicitly NOT treated as barrier presence... it counts as an unconfirmed
gap"). The three pre-fix true positives (`ext_003`, `ext_015`, `ext_021`) all
had `barrier_status = not_mentioned` but happened to trip an existing
exposure phrase ("in the path of", "beneath the load") — proving the barrier
side of the extractor was not the bottleneck, only exposure was. This
matters because it means the fix could be small and targeted rather than a
rewrite of the whole extraction layer.

## Per-category error taxonomy

| Category | Count (of 24) | Example | Notes |
|---|---|---|---|
| **EXPOSURE not recognized despite explicit injury/contact language** | 19 pre-fix / 11 post-fix | `ext_009` ("struck the deck operator in the chest"), `ext_019` ("fatally trapping the inspection team leader"), `ext_016` ("was overcome by hydrogen sulfide gas") | Root cause above. Primary fix target. |
| **BARRIER real-world absence phrasing not recognized as `explicitly_absent`** | ~14/24 land on `not_mentioned` instead | `ext_020` ("Lock-Out/Tag-Out procedures were not in use" -> `not_mentioned`, should be `explicitly_absent` or at least `uncertain`) | Does not block `sif_potential` (see above) but degrades bucket confidence, justification quality, and would matter more once exposure recall improves further. Left unfixed in Phase 7 — see "Deferred" below. |
| **ONTOLOGY GAP: no representable energy/LSR for the hazard** | 5/24 (`ext_007`, `ext_008` diving DCS; `ext_010`, `ext_022` electrical/pressure edge fits; `ext_011`, `ext_023` structural/weather, survival-equipment) | Decompression sickness, wave/structural loading, lifeboat mechanical failure have no clean match among the 14 energy types or 9 LSRs | Expected: ontology targets Indian onshore upstream, not marine diving/offshore-specific hazards. Not a bug — a scope boundary, correctly left `UNKNOWN` in gold rather than force-mapped. |
| **ACTUAL OUTCOME VS POTENTIAL OUTCOME** | 1 deliberate case (`ext_011`) | Wave broke a cabin window; nobody was in the cabin; source itself states "could have caused a serious injury or fatality" | `sif_potential_gold=true` despite `no_exposure`/`no_injury` actually occurring — this narrative was included specifically to test whether Sentinel over-indexes on literal absence-of-injury. Post-fix, Sentinel still returns `NEEDS_MORE_INFO`/false here (a defensible outcome given `is_high_energy=False` for this narrative — see next row — not a clear miss). |
| **ENERGY EXTRACTION false-trigger risk (flagged, not yet realized as an error)** | 1 case (`ext_005`) | Njord A oil spill: an environmental/process-safety narrative with words like "safety system," "shutdown," "barrier" triggered `is_high_energy=True` from the rule gate even though there is no personnel energy-exposure pathway at all | Did **not** produce a false positive this time only because exposure/barrier also came back non-triggering for unrelated reasons — this is a fragile non-failure, not a designed-in safeguard. Documented as a latent risk for Week 2, not fixed now (fixing it safely requires distinguishing "process/environmental safety system" language from "occupational barrier" language, which is a bigger change than Week 1's mandate for minimal fixes). |
| **TRANSFORMER / SCL DISAGREEMENT** | 19/24 pre-fix, 11/24 post-fix | DistilBERT predicted `True` with 0.95-0.98 confidence on nearly every narrative (it was fine-tuned on natural-language classification and generalizes far better than the phrase-list extractor); the SCL reasoner said `False` on all of these | This is the single most actionable signal in the whole exercise: **the transformer already "knows" most of these are SIF-relevant; the deterministic layer's exposure gate is what disagrees.** Because `MODEL_DISAGREEMENT_THRESHOLD=0.70` and the deterministic bucket has to already be `HIGH_CONF_SIF`/`HIGH_CONF_NON_SIF` to escalate (`routing.py`, `reports/week1_baseline.md` §14), most of these disagreements landed in `NEEDS_MORE_INFO` (already a review-queue bucket) rather than being silently accepted as confident non-SIF calls — i.e. **the routing design's conservatism partly absorbed the extraction gap** rather than shipping confident wrong answers. This is a genuinely positive finding about the architecture, not just a failure. |
| **REPORT TOO SHORT / UNFAMILIAR TERMINOLOGY** | 0 clear cases | — | Not observed as a distinct failure mode in this sample; all 24 narratives are full-paragraph investigation-report or safety-alert prose, longer and more technical than typical synthetic UA/UC cards, which is itself a distributional difference worth tracking (see `data/external_eval/README.md` limitations) but did not show up as a distinguishable error category on its own. |
| **CONTRADICTORY EVIDENCE** | 0 cases | — | `consistency_result.contradiction_detected` did not fire on any of the 24 narratives (checked in `sentinel_outputs.jsonl`). |
| **MISSING INFORMATION (`NEEDS_MORE_INFO` / `candidate_needs_info`)** | 18/24 pre-fix, 18/24 post-fix | — | The dominant bucket both before and after the fix. This is the routing layer doing its job as designed (silence is never read as a confirmed barrier) — but an 18/24 "needs more info" rate on real text would flood a human review queue if deployed as-is; see Week 2 priorities. |
| **LSR MAPPING** | Not separately scored (no LSR ground truth field existed prior to this session's annotation) | `annotations.jsonl` now carries `lsr_gold` for future use | Deferred to Week 2: score `cls["lsr_tag"]` against `lsr_gold` once a larger, better-balanced corpus exists; N=24 with several deliberate `UNKNOWN`s is too small to draw a real LSR accuracy number from now. |
| **CONSEQUENCE PATHWAY** | Not separately scored | `annotations.jsonl` carries `credible_consequence_gold` / `consequence_pathway_source` for future use | Same as above — deferred, recorded for Week 2. |

## Representative failures (detail)

### 1. `ext_009` — Scarabeo 8 crush injury (fixed by Phase 7)

- **Text:** "...the RCWM instead activated and moved inward toward the worker...
  The pipe handling equipment... struck the deck operator... resulting in
  crush injuries to both thighs..." *(paraphrase per corpus methodology; see
  narratives.jsonl for exact wording)*
- **Gold:** `sif_potential=true`, `exposure=direct_proximity`, actual outcome
  serious injury.
- **Sentinel before fix:** `exposure=unspecified` -> `sif_potential=False`,
  bucket `NEEDS_MORE_INFO`. Transformer alone: `True`, confidence 0.98.
- **Sentinel after fix:** exposure phrase list now includes "crushed between" /
  "was crushed" -> correctly resolved.
- **Where reasoning failed:** exposure phrase list, not the SCL logic itself.
- **Proposed fix:** data-based (phrase-list expansion). **Implemented in
  Phase 7.**

### 2. `ext_020` — IADC PRS/LOTO near-miss (partially open)

- **Text:** "...Lock-Out/Tag-Out procedures were not in use." (verbatim from
  source)
- **Gold:** barrier LOTO `explicitly_absent`, fall protection
  `confirmed_present` (harness worked as intended), `sif_potential=true`
  (near-miss, no injury).
- **Sentinel (both before and after fix):** `barrier_status=not_mentioned`
  (the phrase "were not in use" is not in `EXPLICIT_ABSENCE_PHRASES`, and is
  not close enough to any `CONFIRMATION_TARGETS` term to trigger the generic
  negated-confirmation path either); `exposure=direct_proximity` after the
  fix ("was pinned"/"pinned the" now matches the PRS-track description) so
  `sif_potential` does resolve `True` post-fix via the exposure route, but
  the *barrier* field is still wrong (should read as at least `uncertain`,
  arguably `explicitly_absent`) and would misinform the justification text
  and any downstream barrier-specific analytics.
- **Where reasoning failed:** `EXPLICIT_ABSENCE_PHRASES` / `CONFIRMATION_TARGETS`
  vocabulary, same category of gap as the exposure fix but on the barrier
  side.
- **Proposed fix:** data-based (add "in use" to `CONFIRMATION_TARGETS` and/or
  "were not in use" / "was not in use" to `EXPLICIT_ABSENCE_PHRASES`).
  **Not implemented in Phase 7** — deliberately deferred because it does not
  change any `sif_potential` outcome in this corpus (barrier `not_mentioned`
  already yields `has_barrier_gap=True`), so fixing it now would be
  optimizing against a metric this corpus can't actually measure the effect
  of, contrary to the "don't optimize blindly" instruction. Flagged as a
  concrete, low-risk Week 2 candidate instead.

### 3. `ext_005` — Njord A oil spill (correct outcome, fragile path)

- **Gold:** `sif_potential=false` (environmental release, no personnel
  exposure pathway).
- **Sentinel:** `is_high_energy=True` (rule gate fired on process/safety
  vocabulary), `exposure=unspecified`, `barrier=not_mentioned` ->
  `sif_potential=False`. **Correct final answer, for a fragile reason** — if
  this narrative had also contained an exposure-triggering phrase (plausible
  for a similar report where someone was nearby during the spill), the
  high-energy misfire would have combined with it to produce a false
  positive on a genuinely non-occupational event.
- **Where reasoning failed:** the high-energy rule gate cannot currently tell
  "process/environmental safety system" language apart from "occupational
  barrier" language.
- **Proposed fix:** left for human review / Week 2 design work, not a
  one-line phrase fix — distinguishing these needs either a scoped keyword
  exclusion list or a coarse pre-classifier for "is this narrative about a
  person's safety at all," and either risks new false negatives on
  legitimate process-safety-adjacent SIF narratives (e.g. a defeated safety
  instrumented system that *did* expose a worker) if done carelessly.

### 4. `ext_017` — Aghorn bystander fatality (open, architectural note)

- **Gold:** a fatality, but the exposed person is the employee's spouse, a
  bystander, not a worker performing a job "activity."
- **Sentinel:** `activity=unspecified activity` (correctly — there is no
  ontology activity to find, because there wasn't one), exposure
  post-fix correctly resolves via "was overcome by" -> `direct_proximity`.
  Because `sif_potential` in `scl_reasoner.py` does not require a resolved
  activity, this case reaches the correct `sif_potential=True` verdict
  despite the missing activity field.
- **Where reasoning held up:** the architecture's decoupling of "activity"
  from the core SIF boolean turned out to be the right call here — worth
  noting as a positive finding, not just cataloguing failures.
- **Proposed fix:** none needed for `sif_potential`; worth flagging for
  Week 2 that `ACTIVITY` and `LOCATION` fields should degrade gracefully
  (as they already do) rather than being required inputs, if Sentinel is
  ever pointed at bystander-involving incidents.

## Inter-annotator agreement

**NOT AVAILABLE.** Only one annotator (this session) produced gold labels.
Raw agreement and Cohen's kappa cannot be computed. This is stated plainly
per the task's own instruction not to fabricate reviewer agreement. See
`docs/WEEK1_ANNOTATION_GUIDELINES.md` header for the same caveat and a
recommendation that a second annotator (ideally an OIL HSE SME) review this
24-row gold set in Week 2 before it is used for any go/no-go decision.
