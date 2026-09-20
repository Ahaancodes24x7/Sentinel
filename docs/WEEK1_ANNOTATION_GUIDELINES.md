# Week 1 External Evaluation — Annotation Guidelines

**Status: single-annotator gold data.** All 24 gold labels in
`data/external_eval/annotations.jsonl` were produced by one annotator (this
Week 1 validation session) reading the public source documents directly. No
second annotator was available in this session, so **no inter-annotator
agreement (raw agreement, Cohen's kappa) can be reported for Week 1** — see
`reports/week1_external_error_analysis.md` for the explicit PASS/FAIL/NOT
AVAILABLE status. Treat every gold label below as a considered judgment call,
not as ground truth beyond dispute; a second annotator should review this set
in Week 2 before it is trusted for any go/no-go decision.

This schema mirrors the ontology already defined in `aiml/configs/ontology.yaml`
and the field semantics implemented in `aiml/src/sif_engine/reasoning/scl_reasoner.py`
and `aiml/src/sif_engine/extraction/evidence_extractor.py` (see
`reports/week1_baseline.md` §4, §12 for the exact source lines this guideline
is grounded in). It does not invent new categories.

## General rule: don't guess

If the source text does not support a confident label, use `UNKNOWN` or
`NEEDS_REVIEW` for that field rather than picking the "closest" option. A
narrative that doesn't mention gas testing has **no barrier evidence for gas
testing**, not a `explicitly_absent` gas-testing barrier. This distinction is
the single most important rule in this document — it is also the exact
distinction Sentinel's own SCL reasoner is built to preserve (barrier
`not_mentioned` is never scored as barrier failure; see baseline report §12).

## 1. SIF Potential

Two separate judgments, not one:

- **`actual_outcome`**: what actually happened — free text plus a coarse
  bucket (`fatality`, `serious_injury`, `minor_injury`, `no_injury`,
  `property_damage_only`, `unknown`).
- **`sif_potential_gold`**: `true` / `false` / `UNKNOWN`. This asks "did this
  report describe exposure to high/uncontrolled energy with an absent or
  degraded barrier, such that a serious or fatal outcome was a realistic
  possibility" — independent of whether that outcome actually occurred.
  **A report with no injury can still be SIF-potential** (e.g. a near-miss
  where a control failed but no one was in the exact path at that instant).
  Conversely a report with a real injury is not automatically SIF-potential
  if the injury arose from low-energy/ergonomic causes with no high-energy
  precursor (e.g. a slip on a wet floor with no other hazard).
- Base the call on the same logical shape the SCL reasoner uses (high-energy
  AND exposure AND barrier gap) — but apply it by human judgment to the
  narrative, not by running the code. This is the label the pipeline's output
  is compared against, so it must be derived independently of Sentinel's own
  reasoning.

## 2. ACTIVITY

Free-text activity phrase closest to `aiml/configs/ontology.yaml`
`activities:` list (32 entries, e.g. "maintenance on process equipment",
"lifting operation with mobile crane"). If the external narrative describes an
activity with no close match in that list (expected often, since the ontology
was built for Indian onshore upstream operations, not Norwegian offshore or US
onshore well services), record the **verbatim activity as described** in
`activity_gold_freetext` and set `activity_in_ontology: false`. Do not force-fit
an activity to the nearest ontology entry if it materially changes the hazard
picture (e.g. "manned underwater diving operation" should not be coerced into
"routine equipment inspection").

## 3. HAZARD

The specific hazardous condition/mechanism named or clearly implied (e.g. "gas
accumulated behind casing", "corroded gas strut", "H2S release in enclosed pump
house"). Free text. Cross-reference to an energy type (§4) separately.

## 4. ENERGY

One or more of the 14 `energy_types` in the ontology
(`stored/electrical energy`, `pressure/hydraulic energy`, `thermal (hot work)`,
`flammable/explosive atmosphere`, `gravitational (suspended load)`,
`fall from height`, `kinetic (line of fire)`, `mechanical/rotating equipment`,
`vehicular/motion`, `atmospheric/asphyxiation`, `chemical/toxic exposure`,
`radiation (NORM/radiography)`, `defeated safety system`,
`low-energy/ergonomic`). A narrative can genuinely involve more than one; list
all that apply and mark one `primary_energy`. If the energy source doesn't map
cleanly (e.g. decompression sickness from diving, or wave/structural load from
a storm), record `energy_gold_freetext` and set `energy_in_ontology: false`
rather than mis-mapping it to the nearest existing category.

## 5. EXPOSURE

One of `direct_proximity`, `indirect_proximity`, `no_exposure`, or `UNKNOWN`.

- `direct_proximity`: a person was in the direct path of the energy release
  (e.g. "struck the deck operator in the chest", "pinned the floorman's arm").
- `indirect_proximity`: a person was in the general area/facility but not in
  the direct release path (e.g. "no personnel were aboard" for an unmanned
  platform fire is `no_exposure`; a person elsewhere on a manned facility
  during a contained release could be `indirect_proximity`).
- `no_exposure`: explicitly no one was present/at risk.
- **Negation matters as much as it does for barriers.** "No personnel were in
  the vicinity" is `no_exposure`, not indirect — do not let the word
  "vicinity" alone trigger `indirect_proximity` (this exact suppression rule
  already exists in `evidence_extractor.extract_exposure`; the gold label
  should reflect the same semantics the code is trying to implement, so a
  disagreement here is diagnostic, not a labeling bug).

## 6. BARRIER / 7. BARRIER STATUS

Identify the specific barrier(s) relevant to the energy/hazard (map to
`aiml/configs/ontology.yaml` `barrier_types:` where it fits: Energy isolation &
LOTO, Permit to work, Gas testing & atmospheric monitoring, Exclusion zone &
barricading, Fall protection, Machine guarding, Traffic & journey management,
Safety instrumented system, Lifting plan & rigging control). For each relevant
barrier, assign exactly one status:

- **`confirmed_present`** — text affirmatively states the barrier was in place
  and functioning as intended at the relevant moment.
- **`uncertain`** — text mentions the barrier but its status/effectiveness at
  the critical moment is ambiguous or contested.
- **`explicitly_absent`** — text affirmatively states the barrier was missing,
  bypassed, defeated, not performed, or failed (e.g. "lock-out/tag-out
  procedures were not in use", "no mechanical barrier was installed").
- **`not_mentioned`** — the barrier is simply never discussed.

**`not_mentioned` is NOT equivalent to barrier failure.** If a narrative about
a lifting incident never discusses gas testing, gas testing is `not_mentioned`
for that report — it is not evidence gas testing failed, because gas testing
may not even be a relevant barrier for that hazard. Only label
`explicitly_absent` when the text itself says or clearly implies the barrier
did not exist or did not function.

## 8. CREDIBLE CONSEQUENCE

Free text: the realistic worst-case outcome given the energy/exposure/barrier
combination, distinguishing it from what actually happened (§1). Many of the
external reports state this explicitly ("could have resulted in severe
injuries...or death", "had circumstances been only slightly different") —
prefer the source's own credible-consequence language when present, and mark
`consequence_pathway_source: "source_stated"` vs `"annotator_inferred"`
accordingly.

## 9. LIFE-SAVING RULE (LSR)

One of the 9 IOGP Report 459 rules (`ontology.yaml` `life_saving_rules:`):
Bypassing Safety Controls, Confined Space, Driving, Energy Isolation, Hot Work,
Line of Fire, Safe Mechanical Lifting, Work Authorisation, Working at Height.
Pick the rule the source narrative most directly engages. If none applies
cleanly (e.g. a structural wave-damage incident with no clear LSR nexus), use
`UNKNOWN` rather than forcing a mapping — do not silently default to a
plausible-sounding rule just because one must be picked.

## 10. LOCATION / CONTEXT

Free text: facility name, facility type (drilling rig / production platform /
onshore plant / pipeline / waterflood station / etc.), and jurisdiction —
taken directly from `source_documents.jsonl`, not re-derived from the
narrative text alone (the narrative excerpt itself may not restate the
facility name every time).

## UNKNOWN vs NEEDS_REVIEW

- `UNKNOWN`: the source material genuinely does not contain enough information
  to answer, and more information would not obviously be available even from
  the full source document (already checked).
- `NEEDS_REVIEW`: the annotator is uncertain, believes a domain expert (OIL HSE
  SME) would resolve it, or the case sits on a genuine boundary between two
  categories (e.g. `uncertain` vs `explicitly_absent` for a barrier). Do not
  silently pick a side; flag it.

Every field in `data/external_eval/annotations.jsonl` uses one of these two
values wherever the annotator was not confident, rather than a forced guess.
