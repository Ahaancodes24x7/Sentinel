# Week 1 Baseline — Frozen Architecture & Reproducibility Snapshot

**Date:** 2026-09-16
**HEAD commit at time of snapshot:** `652780e` — "Connect fine-tuned transformer to live pipeline, ground interventions in evidence"
**Scope:** Read-only documentation. No source files were modified while producing this report (test/eval runs only).

---

## 0. Git status at snapshot time

```
On branch main
Changes not staged for commit:
  modified:   aiml/notebooks/01_eda_synthetic_data.ipynb
  deleted:    aiml/reports/mlp_model_evaluation_report.md
```

```
git log --oneline -10
652780e Connect fine-tuned transformer to live pipeline, ground interventions in evidence
c1e4f43 Gitignore aiml/models/transformers/ - Trainer checkpoints (incl. 1.1GB optimizer.pt state) were committed by accident and stripped from history in the previous commit
cdd3e31 Merge remote main (stale, superseded by local history) using ours strategy - no unique remote content lost, verified README byte-identical earlier
a2c221e Merge Sentinel repo's README update (identical content, reconciles diverged history)
f770b2a Update README.md
4ea1a4e Update README.md
94a850f Read me added
b59a427 Inferences engine
cb7267d CCTV scene analysis, self-filing complaints, and ESP32 voice reporting
30b7ca0 CCTV scene analysis, self-filing complaints, and ESP32 voice reporting
```

The two working-tree changes (a notebook and a deleted stale report) predate this Week 1 work and were **not touched or reverted** during Phase 1.

**IMPORTANT DISCREPANCY FLAGGED:** the Week 1 task brief states "the current synthetic evaluation contains 3,000 reports." This is **stale**. The dataset actually in the repo (`aiml/data/synthetic/synthetic_uauc_reports.csv`, confirmed by row count, `dataset_card.md`, and `aiml/reports/metrics.json`) contains **25,000 rows** (`n_total: 25000`, `n_train: 15000`, `n_val: 5000`, `n_test: 5000`), generated with seed 42. 3,000 rows was true of an earlier version of the dataset (see the now-deleted `aiml/reports/mlp_model_evaluation_report.md`, and the comment in `aiml/scripts/_transformer_common.py:11-20` that explicitly documents this history). All metrics reported below are against the current 25,000-row / 5,000-row-test dataset, not 3,000.

---

## 1. Active SIF model in the live inference path

`aiml/src/sif_engine/inference/model_registry.py:10-15,44` resolves the active model in this order:
1. `SENTINEL_SIF_MODEL` env var if set to one of `baseline2` / `mlp` / `transformer`.
2. Otherwise: **`transformer`** if `models/transformers/distilbert_finetuned/final/` exists on disk (`ModelRegistry.is_transformer_available()`, line 78-83), **else `baseline2`**.

On this machine the checkpoint **is present** (see §18), so the active live model is the **fine-tuned DistilBERT** (`inference/transformer.py`, `MODEL_VERSION = "distilbert-finetuned-v2.0"`).

Three models are registered (`model_registry.py:27` `AVAILABLE_MODELS = ("baseline2", "mlp", "transformer")`):
- `baseline2` — TF-IDF + Logistic Regression (`inference/baseline2.py`), always available, no download. This is the **fallback** used on any fresh clone that lacks the (gitignored) transformer checkpoint.
- `mlp` — an MLP neural net (`inference/mlp.py`), loaded from `aiml/models/mlp/`. Present but **not the default** on any clone — only reachable via explicit `model_name`/`SENTINEL_SIF_MODEL=mlp`.
- `transformer` — the fine-tuned DistilBERT (`inference/transformer.py`), the model actually wired into the default live path when its checkpoint exists.

`aiml/models/sif_classifier_baseline2.pkl`, `aiml/models/lsr_classifier_baseline2b.pkl`, `aiml/models/baseline2/`, `aiml/models/mlp/`, `aiml/models/energy/`, `aiml/models/barrier/` are all present on disk; `baseline2` and its LSR tagger remain load-bearing (the transformer borrows the baseline2 LSR tagger — see §2) rather than legacy/dead artifacts. `aiml/scripts/train_transformer_part1_bert_xgboost.py` (frozen-embedding + XGBoost) and `train_transformer_part3_hybrid.py` (hybrid variant) exist but are **not** wired into `model_registry.py` at all — they produced `aiml/reports/transformer_part1_metrics.json` for comparison purposes only and are not selectable at inference time.

Call graph for a live request: `aiml/api/inference_server.py:14` (`POST /infer/single`) → `sif_engine.pipeline.run_single` (`aiml/src/sif_engine/pipeline.py:278`) → `energy_classifier.classify_energy(...)` (`aiml/src/sif_engine/extraction/energy_classifier.py:147`) → `model_registry.get_active_model()` → `TransformerModel.predict()`.

---

## 2. Hugging Face checkpoint

Base checkpoint: **`distilbert-base-uncased`** (confirmed both in `aiml/scripts/train_transformer_part2_finetune.py:12` default invocation and in the saved `config.json`'s architecture `DistilBertForSequenceClassification`, `vocab_size: 30522`, `n_layers: 6`, `n_heads: 12`, `dim: 768`, `hidden_dim: 3072` — the standard DistilBERT-base-uncased shape).

Fine-tuned **end-to-end** (not frozen-embedding + head) as a binary sequence classifier, `num_labels=2` (`train_transformer_part2_finetune.py:126-128`). Saved checkpoint on disk at `aiml/models/transformers/distilbert_finetuned/final/` (gitignored — see §19/20).

The fine-tuned checkpoint has **no LSR head**; LSR tagging for the transformer backend is delegated to the existing Baseline2 TF-IDF+LogReg LSR tagger pickle (`aiml/models/baseline2/lsr_classifier_baseline2b.pkl`, loaded in `inference/transformer.py:76-82`, applied in `_predict_lsr` line 93-99). This is documented explicitly in the module docstring (`inference/transformer.py:13-17`).

Other encoders supported by the *same* training script but **not currently active** in the registry: `microsoft/deberta-v3-small`, `microsoft/deberta-v3-base` (`train_transformer_part2_finetune.py:13-14`).

---

## 3. Tokenizer

- `AutoTokenizer.from_pretrained(<checkpoint dir>)` — `BertTokenizer` backend (`tokenizer_config.json`: `"tokenizer_class": "BertTokenizer"`, `"do_lower_case": true`).
- `model_max_length: 512` in the tokenizer config, but the pipeline **truncates to `MAX_LENGTH = 128`** at both train time (`train_transformer_part2_finetune.py:47`) and inference time (`inference/transformer.py:29`, used in `predict()` line 109: `truncation=True, max_length=MAX_LENGTH`).
- Special tokens: `[CLS]`, `[SEP]`, `[PAD]` (pad_token_id 0), `[MASK]`, `[UNK]` — standard BERT-uncased vocabulary.
- Input text is run through the Stage-0 preprocessing pipeline (`preprocess_report`, see §9) **before** tokenization (`inference/transformer.py:107`), i.e. the tokenizer never sees raw un-normalized text.

---

## 4. Model configuration

`aiml/configs/model_config.yaml` (verbatim, 3 lines):
```yaml
confidence_thresholds: {high_conf: 0.75, low_conf: 0.25}
paths: {models_dir: "../models", data_dir: "../data"}
```
The comment on line 1 (`# Tune these values once real evaluation data exists.`) is itself evidence the current 0.75/0.25 split has never been calibrated against anything but the synthetic set.

`aiml/configs/ontology.yaml` (`version: "2.0.0"`, `taxonomy_source: "EEI SCL Model (energy wheel) + IOGP Report 459 Life-Saving Rules"`) defines the single shared taxonomy consumed by data generation, the energy classifier, and the SCL reasoner:
- **9 Life-Saving Rules** (IOGP Report 459): Bypassing Safety Controls, Confined Space, Driving, Energy Isolation, Hot Work, Line of Fire, Safe Mechanical Lifting, Work Authorisation, Working at Height.
- **14 energy types** (EEI energy-wheel derived), each with `is_high_energy` (bool), `lsr_tag`, `magnitude_class` (1-5), and a `keywords` list (e.g. `stored/electrical energy`, `pressure/hydraulic energy`, `thermal (hot work)`, `flammable/explosive atmosphere`, `gravitational (suspended load)`, `mechanical/rotating equipment`, `kinetic (line of fire)`, `defeated safety system`, `vehicular/motion`, `atmospheric/asphyxiation`, `fall from height`, `chemical/toxic exposure`, `radiation (NORM/radiography)`, `low-energy/ergonomic`).
- `activities:` (line 185) and `sites:` (line 257) lists — the latter is the **synthetic/prototype site vocabulary** (Rig 4/7/12, Plant C/D, Terminal A, Well Site B/F, Field Station 2/5, Pipeline Section 9, Workshop Central), used both by the generator and by `site_intelligence/site_registry.py` for resolving location text.
- The ontology file does **not** define `barrier_status_phrases` or `exposure_phrases` keys (confirmed by direct grep — only `activities:` and `sites:` top-level keys of that shape exist). This matters because `pipeline.py`'s `_extract_heuristic_fields()` function (lines 62-261) reads exactly those two missing keys via `ontology.get(..., {})` — see §5 dead-code note.

---

## 5. Inference code path (end-to-end)

`aiml/api/inference_server.py` — a bare `APIRouter` (not a standalone app; the backend team mounts it) exposing:
- `POST /infer/single` → `run_single(request.text)`
- `POST /infer/batch` → `run_batch(reports)`

`sif_engine.pipeline.run_single()` (`aiml/src/sif_engine/pipeline.py:278-627`) stages:

1. **Stage 0 — Preprocessing**: `preprocess_report_with_metadata(raw_text)` (see §9).
2. **Stage 1 — Evidence extraction**: `extract_evidence(raw_text, ontology_activities=...)` from `extraction/evidence_extractor.py` — activity, hazard-category matches, exposure (negation-aware), 4-state barrier status, location. This is the function **actually used**; it is a distinct, separate implementation from the unused `_extract_heuristic_fields()` defined at the top of `pipeline.py` (lines 62-261), which is **dead code** — it is never called anywhere in the codebase (confirmed by grep: the only occurrence of the identifier is its own `def`). It duplicates roughly the same extraction responsibility using different (looser) keyword lists and reads two ontology keys (`barrier_status_phrases`, `exposure_phrases`) that do not exist in `ontology.yaml`, so if it were ever called it would silently return `"uncertain"` / `"direct_proximity"` defaults for every report. This is a documentation-worthy latent hazard even though it currently has zero effect on production behaviour.
3. **Energy classification**: `classify_energy(raw_text, preprocessed_text, hazard_category, model_name)` (`extraction/energy_classifier.py:147-236`). This is the **single call site where the active learned model (baseline2/mlp/transformer) is invoked** (`model_registry.get_model(model_name) or get_active_model()`, line 166-167). It combines:
   - a **deterministic rule/evidence high-energy gate** (`evaluate_high_energy_gate`, lines 99-144) — authoritative for the boolean `is_high_energy` decision;
   - the **learned model's descriptive energy-type label + LSR tag + its own binary `sif_potential` signal**, carried through untouched as `sif_signal` (lines 181-185) specifically so Stage 3 can cross-check it later.
   - The docstring states the rule gate **outperforms** a multiclass TF-IDF classifier on SIF recall (0.779 vs 0.716) and F2 (0.781 vs 0.738) for the high-energy decision specifically — i.e. even with the transformer active, the authoritative high-energy boolean is **not** transformer-derived.
4. **Consistency validation**: `validate_consistency(...)` (`reasoning/consistency.py`) — contradiction/near-miss checks between evidence and energy classification.
5. **Stage 2 — SCL reasoner**: `reason(evidence, energy_classification, consistency_result)` (`reasoning/scl_reasoner.py:65-387`) — the **deterministic, authoritative** verdict engine (see §12).
6. **Stage 3 — Confidence & routing**: `route_prediction(...)` (`confidence/routing.py:212-281`) — combines the SCL reasoner's own evidence-strength routing (`_route_deterministic`) with the **cross-check against the learned model's `sif_signal`** (see §13/14 — this is where transformer-vs-reasoner disagreement can escalate a bucket to `LOW_CONF_REVIEW`).

The transformer's prediction and the SCL reasoner's verdict are combined **only** at Stage 3 (`route_prediction`), not earlier — the reasoner's `sif_potential` boolean is computed with zero knowledge of what the transformer said; the transformer's opinion is folded in afterward purely as a disagreement check, never as an input to the reasoning itself.

---

## 6. Training code (transformer, Part 2 fine-tune)

`aiml/scripts/train_transformer_part2_finetune.py`:
- CLI defaults: `--epochs 4`, `--batch_size 16` (`per_device_eval_batch_size=64`), `--lr 2e-5`.
- Loss: `nn.CrossEntropyLoss(weight=class_weights)` inside a custom `WeightedTrainer.compute_loss` (lines 87-103) — **not** the vanilla HF Trainer loss.
- Class weights: **inverse-frequency**, normalized to average 1.0 — `w_pos = (n_pos+n_neg)/(2*n_pos)`, `w_neg = (n_pos+n_neg)/(2*n_neg)` (lines 133-139). The committed metrics JSON records the actual values used: `class_weights: [0.8803850412368774, 1.1572288274765015]` (neg, pos) — consistent with a ~43.2% positive training split (higher weight on the minority-ish positive class).
- `metric_for_best_model="recall"`, `greater_is_better=True`, `load_best_model_at_end=True`, `save_strategy="epoch"`, `eval_strategy="epoch"`, `save_total_limit=1` — model selection across epochs is **recall-first**, explicitly stated in the module docstring as a deliberate project stance ("a missed SIF-potential report is categorically worse than an extra false positive").
- `weight_decay=0.01`, `fp16` only enabled on CUDA and only for non-DeBERTa encoders (DistilBERT on CUDA would get fp16; this run used `"device": "cuda"` per the metrics JSON's `hardware` block, GPU `"NVIDIA GeForce RTX 2050"`).
- `seed=42` (`TrainingArguments(..., seed=42)`, line 164) — HF Trainer's own seed, separate from the data-split seed (also 42, but a different RNG stream — see §8).
- `torch_dtype=torch.float32` forced regardless of checkpoint's stored dtype (line 127) — a DeBERTa-specific fix that is a no-op for `distilbert-base-uncased` (which is fp32 already) but kept uniform across all three supported encoders.

Train/val/test sizes actually used (from the reproduction run, §18): **15,000 / 5,000 / 5,000**.

---

## 7. Dataset generation code

`aiml/src/sif_engine/data_generation/synthetic_generator.py:811` `generate(n=25000, seed=42, months=12)`, invoked via `aiml/scripts/generate_synthetic_data.py` (`--seed` default `42`, `--n`, `--months` CLI args). `rng = random.Random(seed)` (line 813) — a single seeded `random.Random` instance drives the entire corpus, per the module's own comment (line 35) "deliberately seeded so the clustering, association-mining and CUSUM [detectors] ... [are reproducible]".

Per `dataset_card.md` (auto-generated by `write_dataset_card`, `generate_synthetic_data.py:27`):
- Labelling rule (ground truth, independent of stated outcome): `sif_potential = high_energy(energy_type) AND exposure != no_exposure AND NOT (barrier confirmed AND barrier is a DIRECT control)`.
- 3% injected label ambiguity/noise on top of the noise-free ground truth (`sif_potential_truth` retained separately for label-noise-robustness analysis) — positive rate 43.2% as labelled vs 42.8% noise-free.
- Injected realism: abbreviation substitution (PTW, LOTO, JSA, H2S, SIMOPS), field typos, code-mixed Hindi/Assamese-influenced phrasing on ~35% of noisy rows, terse fragments (~16%), ~35% of rows left clean.
- 7 deliberately "planted" incident patterns (established/emerging/sporadic-high-severity) at specific sites, so downstream pattern-mining/trend-detection modules have real signal to find — e.g. `p_isolation_handover` (Rig 7, stored/electrical energy, uncertain barrier, n=260) through `p_radiography_rare` (Field Station 5, n=9).
- The card's own "Known limitations" section (verbatim): *"Generated from a finite phrase bank; a model can overfit the generator. Real reports contain equipment tags, org-specific jargon and narrative digressions this generator does not reproduce. Real validation requires an OIL SME-reviewed gold set on real exports."* — this is the exact gap Week 1 Phase 2-6 exists to probe.

---

## 8. Train/test split logic and random seeds

Two **separate, independently-seeded** randomness sources exist in this project — worth being precise about since both use the literal value `42`:

1. **Data generation seed**: `random.Random(seed=42)` inside `synthetic_generator.generate()` — controls which phrases/templates/noise get sampled into which of the 25,000 rows.
2. **Train/val/test split seed**: `RANDOM_STATE = 42` in `aiml/scripts/_transformer_common.py:53`, used by `sklearn.model_selection.train_test_split` **twice**, stratified on `sif_potential`:
   - `train_df, temp_df = train_test_split(df, test_size=0.4, random_state=42, stratify=df.sif_potential)` → 60% train.
   - `val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42, stratify=temp_df.sif_potential)` → remaining 40% split evenly into 20% val / 20% test.
   - Result: **15,000 / 5,000 / 5,000** for a 25,000-row corpus. This is documented in `_transformer_common.py`'s own module docstring (lines 10-20) as a **deliberate deviation** from an older task-brief instruction of `test_size=0.2` (80/20), made explicitly so the transformer variants are benchmarked on the *exact same* split as the existing B1-B5 baseline ladder in `aiml/reports/model_evaluation_report.md`, not a differently-sized split that would only be "similarly" comparable.
3. `TrainingArguments(seed=42)` in the fine-tuning script (`train_transformer_part2_finetune.py:164`) — HF Trainer's own seed for shuffling/dropout/init, a third, separate use of the same integer.

All three seeds are hardcoded `42`, not derived from each other, and not configurable via `model_config.yaml`.

---

## 9. Preprocessing pipeline

`aiml/src/sif_engine/preprocessing/pipeline.py`, `preprocess_report(text, lowercase=True)`, run in this fixed order (`pipeline.py:24-30`):
1. `expand_abbreviations(text)` — case-sensitive, **before** lowercasing (`abbreviations.py`).
2. `translate_code_mixed(text)` — code-mixed Hindi/Assamese-influenced phrase normalization (`code_mixed.py`).
3. `.lower()` if `lowercase=True`.
4. `correct_typos(text)` — typo correction (`typo_correction.py`), run **after** lowercasing.
5. `normalize_whitespace_punct(text)` — strips `(...ref...)`-style parenthetical noise, strips `#\d+` tag numbers (e.g. "LOTO tag #482"), removes space-before-punctuation, collapses whitespace — explicitly ordered **last** because earlier content-removing substitutions can leave double-spaces that only this final collapse step cleans up (documented in the function's own docstring, `pipeline.py:9-13`).

`preprocess_report_with_metadata()` runs the same 5 steps but returns intermediate text at each stage (used by `pipeline.run_single`'s `stage_metadata.stage0`, exposed for UI/audit purposes).

This exact function (`preprocess_report`) is what both the transformer's `predict()` (`inference/transformer.py:107`) and the training script's `build_datasets()` (`train_transformer_part2_finetune.py:50-52`, via `text_proc` column built in `_transformer_common.load_split()`) apply — i.e. train-time and inference-time preprocessing are guaranteed identical because they call the same function, not parallel reimplementations.

---

## 10. Thresholds

- **Confidence routing thresholds** (`aiml/configs/model_config.yaml`): `high_conf: 0.75`, `low_conf: 0.25` — loaded by `confidence/routing.py:_load_thresholds()` and used both in `_route_deterministic` (`strength >= high_th` for `HIGH_CONF_SIF`) and in the standalone legacy `route()` function.
- **Transformer's own decision boundary**: `sif_prob >= 0.5` (`inference/transformer.py:122`), with the *same* 0.75/0.25 split applied to the transformer's own probability to assign its own internal bucket label (lines 123-130) — explicitly kept identical to the other two backends' bucket semantics "so switching models via `SENTINEL_SIF_MODEL` changes which model answers, not what the bucket boundaries mean" (comment, lines 117-121).
- **`MODEL_DISAGREEMENT_THRESHOLD = 0.70`** (`confidence/routing.py:142`) — the learned model's own confidence must be ≥0.70 for a disagreement with the SCL reasoner to be treated as a real signal worth escalating (rather than review-queue noise from a near-coin-flip model opinion).
- **Barrier/exposure strength weights** used in `evidence_strength()` (`routing.py:52-70`): `W_ENERGY=0.30`, `W_BARRIER=0.40`, `W_EXPOSURE=0.30`; `_BARRIER_STRENGTH` (`explicitly_absent`:1.00, `uncertain`:0.65, `not_mentioned`:0.50, `confirmed_present`/`confirmed`:0.00); `_EXPOSURE_STRENGTH` (`direct_proximity`:1.00, `indirect_proximity`:0.55, `no_exposure`:0.00, `unspecified`/`unknown`:0.35). The module docstring states these are "stated in the open rather than tuned to make the demo numbers look good" and flags them as needing calibration "with OIL HSE SMEs against real review outcomes" (`routing.py:48-52`) — i.e. these weights are **acknowledged-uncalibrated** by the codebase's own authors, not just by this audit.
- **Barrier gap-severity scalars** (`extraction/evidence_extractor.py`): `confirmed`=0.0, `uncertain`=0.6, `explicitly_absent`=1.0, `not_mentioned`=`None`.
- **Barrier proximity window**: `BARRIER_PROXIMITY_TOKENS = 8` tokens (`evidence_extractor.py:346`) — how close a confirmation word must be to a barrier mention to count as confirming it; `window_words=4` default parameter to `extract_barrier_status`.
- **High-energy rule-gate confidence**: `min(0.70 + 0.05 * len(matched_cues), 0.95)` when cues match (`energy_classifier.py:121`), `0.80` for hazard-category fallback, `0.85` for the negative (no high-energy evidence) case.
- **Single-token cue exclusion rule**: a high-energy cue only fires the rule gate if it is multi-word or ≥6 characters (`energy_classifier.py:94-96`) — an explicit anti-false-positive guard against generic single tokens like "guard", "pressure", "chemical".

---

## 11. Class weights in training

Covered in §6: inverse-frequency, normalized to mean 1.0, computed fresh from the actual training split's label counts each run (`train_transformer_part2_finetune.py:133-139`), not a fixed hardcoded ratio. Committed run: `[0.8803850412368774, 1.1572288274765015]` for `[neg, pos]`.

---

## 12. SCL reasoning logic (deterministic, authoritative)

`aiml/src/sif_engine/reasoning/scl_reasoner.py`, `reason()` (lines 65-387) — this is the component the task brief calls "the deterministic SCL safety reasoner [that] still owns the safety verdict." Confirmed: `sif_potential` here is computed **without reference to any learned-model output** — its only inputs are `evidence` (from `extraction/evidence_extractor.py`), `energy_classification` (from `energy_classifier.classify_energy`, itself a rule-gate + optional descriptive-label-only use of the model — see §5), and `consistency_result`.

Core decision (lines 163-180):
```python
sif_potential = bool(
    (is_high_energy and has_barrier_gap and has_exposure) or
    (is_valid_near_miss and is_high_energy and is_direct_exposure and barrier_status != "confirmed_present")
)
# SCL "direct control" override:
if barrier_status == "confirmed_present":
    sif_potential = bool(is_high_energy and has_exposure and not barrier_is_direct)
```
- The **direct-control test** (`_barrier_is_direct`, delegating to `data_generation/ontology.is_direct_control`) means a *confirmed administrative* control (e.g. a permit) does **not** clear a high-energy exposure the way a confirmed *engineering* control does — a confirmed permit alone cannot zero out an otherwise-valid SIF call.
- **4 barrier states** are supported end-to-end, exactly as required: `confirmed_present` (aliased in also from legacy `confirmed`), `uncertain`, `explicitly_absent`, `not_mentioned` (`_normalize_barrier_status`, lines 19-31). Internally normalized, then re-exposed via `_legacy_barrier_label` for backward-compatible field names (`confirmed_present`→`confirmed`, others unchanged).
- **`not_mentioned` is explicitly NOT treated as barrier presence or as barrier failure** — it counts as an *unconfirmed* gap (`has_barrier_gap = True`) **and** separately raises `candidate_needs_info = True` (lines 121-131), with an inline comment stating this is deliberately the same failure mode "the SCL model and the research blueprint both single out" (reading silence as safety). The justification text generated for this case explicitly says: *"Absence of mention is not read as a confirmed barrier — barrier verification required"* (lines 214-218).
- **Exposure**: uses the extractor's `exposure.label` plus an additional inline explicit-phrase check (`"worker was exposed"`, `"exposed to an energized electrical component"`, etc., lines 138-143) as a second-pass upgrade path from `unspecified` → `direct_proximity`. `has_exposure` is true for `direct_proximity` or `indirect_proximity`; negation/absence is handled upstream in `extraction/evidence_extractor.extract_exposure` (see §5 quote of that function — explicit no-exposure phrases checked *before* proximity phrases, with sub-span filtering so a proximity phrase embedded inside a no-exposure phrase, e.g. "vicinity" inside "no personnel were in the vicinity", is correctly suppressed rather than double-counted).
- **Credible consequence**: delegated to `reasoning/credible_consequence.evaluate_credible_consequence(energy_type, hazard_category, exposure_label)` — ontology-driven mapping to a `primary_consequence` / `potential_severity` / LSR tag, not itself scored by any learned model.
- Produces a fully inspectable structured object: `reasoning_steps` (7 numbered steps: Activity → Hazard/Energy → Exposure → Barrier → Credible consequence → SIF potential → LSR), `decision_factors`, `missing_information`, `contradictions`, plain-language `justification`, and legacy-compatible duplicate keys for backward compatibility with older consumers.

---

## 13. Confidence routing — actual bucket names and logic

`aiml/src/sif_engine/confidence/routing.py:41-46` — the **actual implemented enum matches the task brief's names exactly**:
```python
HIGH_CONF_SIF, LOW_CONF_REVIEW, HIGH_CONF_NON_SIF, NEEDS_MORE_INFO
```
(No divergence found between brief and code here — worth confirming explicitly since other assumptions in the brief, e.g. dataset size, did not hold.)

`_route_deterministic()` (lines 145-209) logic order:
0. Active internal contradiction (`consistency_result.contradiction_detected`) → always `LOW_CONF_REVIEW`, regardless of direction.
1. `_insufficient_evidence()` (lines 116-135: only true when energy is high-energy AND barrier is `not_mentioned` AND (exposure is unspecified/unknown OR energy source is a fallback, i.e. no model ran)) → `NEEDS_MORE_INFO`. A confidently low-energy report is **never** routed here even with missing barrier/exposure detail, to avoid flooding the review queue with housekeeping trivia.
2. Barrier `not_mentioned` on a high-energy report (and not already caught above) → `NEEDS_MORE_INFO` — silence is never read as a confirmed control, but no confidence is claimed either way.
3. If `sif_potential`: `HIGH_CONF_SIF` requires `strength >= 0.75` **and** internally consistent **and** no warnings **and** barrier status is not `uncertain` (an uncertain barrier can support a precursor call but never a *high-confidence* one); otherwise `LOW_CONF_REVIEW`.
4. If not `sif_potential`: `HIGH_CONF_NON_SIF` requires **positive** evidence against (low energy, OR a confirmed barrier, OR confirmed no-exposure) **and** consistent **and** barrier not `uncertain`; otherwise falls through to `NEEDS_MORE_INFO` (if `candidate_needs_info`) or `LOW_CONF_REVIEW`.

`evidence_strength()` (lines 87-113) combines the three SCL axes: `W_ENERGY*energy_component + W_BARRIER*barrier_component + W_EXPOSURE*exposure_component` (weights in §10); `energy_component` is penalized ×0.25 if not high-energy — "low energy cannot make a precursor" is baked in as a hard multiplier, not just a threshold.

Confidence is reported "in the direction of the decision actually made" (line 165-168: `confidence = strength if sif_potential else (1.0 - strength)`, then reduced by the consistency `penalty` and clamped to `[0.10, 1.0]`) — i.e. a confident non-SIF call reads as high confidence, not low, which is a deliberate design choice worth knowing when interpreting the number downstream.

---

## 14. Transformer-vs-reasoner cross-check / disagreement escalation

`route_prediction()` (`confidence/routing.py:212-281`) is the **single place** this happens:
1. Runs `_route_deterministic(...)` first — the SCL chain decides the bucket **with zero knowledge of the model's opinion.**
2. If `model_signal` (the active model's own `{sif_potential, confidence, model_version}` for this report, threaded through from `energy_classifier.classify_energy`'s `sif_signal`, §5) is present:
   - Records `agrees = (model_sif_potential == sif_potential)` in `model_agreement` (always surfaced, whether or not it changes the bucket — the UI shows agreement as corroborating evidence, never folded into the confidence number itself).
   - **Confident disagreement** = `not agrees and model_conf >= MODEL_DISAGREEMENT_THRESHOLD (0.70)`. If confident disagreement **and** the deterministic bucket was `HIGH_CONF_SIF` or `HIGH_CONF_NON_SIF`, the bucket is **demoted to `LOW_CONF_REVIEW`** and `model_agreement.escalated = True` (lines 274-279).
   - A disagreement with model confidence below 0.70 does **not** escalate — treated as noise, not a real signal (comment lines 138-142).
3. `pipeline.py:_model_agreement_detail()` renders this into `reasoning_steps` step 8 ("Model cross-check") as one of three human-readable sentences: agrees / disagrees-and-escalated / disagrees-but-below-threshold.

This confirms the task brief's framing precisely: "Transformer-vs-reasoner disagreement escalates cases to LOW_CONF_REVIEW" is accurate and specifically gated on the model's own confidence exceeding 0.70 — a low-confidence transformer opinion cannot override or contest a confident deterministic verdict.

---

## Reproducibility

### 15-17. Test / build results (fresh run, this session)

| Suite | Command | Result |
|---|---|---|
| aiml | `cd aiml && python -m pytest tests/ -q` | **105 passed** in 83.34s, 0 failures |
| backend | `cd backend && python -m pytest tests/ -q` | **41 passed** in 14.15s, 1 warning (unrelated `PendingDeprecationWarning` from `starlette.formparsers`, not a project code issue), 0 failures |
| frontend | `cd frontend && npm run build` (`tsc -b && vite build`) | **Build succeeded**, 0 TypeScript errors. Vite emits a non-blocking config-loader deprecation notice (`__dirname` usage) and a chunk-size-over-500kB advisory — neither is an error. |
| frontend lint | `cd frontend && npm run lint` (`oxlint`) | **0 errors**, 16 pre-existing warnings (React fast-refresh / effect-setState / exhaustive-deps style warnings across several page/component files) — not new, not blocking. |

This matches the task brief's stated baseline exactly: 105 aiml tests, 41 backend tests, frontend build/lint clean.

### 18. DistilBERT evaluation — reproduced fresh, not just read from file

The gitignored checkpoint directory **is present** on this machine at `aiml/models/transformers/distilbert_finetuned/final/` (contains `config.json`, `model.safetensors`, `tokenizer.json`, `tokenizer_config.json`, `training_args.bin`) — so re-evaluation without retraining was possible and was performed.

Method: loaded `_transformer_common.load_split()` (same 60/20/20 seed-42 stratified split used at training time) to regenerate the identical 5,000-row test set, loaded the checkpoint with `AutoModelForSequenceClassification.from_pretrained` + `AutoTokenizer.from_pretrained` exactly as `inference/transformer.py` does, ran batched inference (`max_length=128`, truncation on, no retraining, no gradient updates), and computed metrics with the project's own `_transformer_common.compute_metrics` (identical formulas to the ones used to produce the committed JSON).

**Freshly reproduced (this session, 5,000-row test split):**
```json
{
  "precision": 0.9625,
  "recall": 0.962,
  "f1": 0.9623,
  "f2": 0.9621,
  "roc_auc": 0.9703,
  "pr_auc": 0.9602,
  "brier": 0.0312,
  "accuracy": 0.9674,
  "flagged_fraction": 0.4318,
  "confusion": {"tn": 2759, "fp": 81, "fn": 82, "tp": 2078}
}
```

**Committed** (`aiml/reports/transformer_part2_distilbert_finetuned_metrics.json`, produced at training time):
```json
{
  "precision": 0.9625,
  "recall": 0.962,
  "f1": 0.9623,
  "f2": 0.9621,
  "roc_auc": 0.9703,
  "pr_auc": 0.9601,
  "brier": 0.0312,
  "accuracy": 0.9674,
  "flagged_fraction": 0.4318,
  "confusion": {"tn": 2759, "fp": 81, "fn": 82, "tp": 2078}
}
```

### 19. Comparison / discrepancy check

**Match:** precision, recall, F1, F2, ROC-AUC, Brier, accuracy, flagged fraction, and the full confusion matrix (tn/fp/fn/tp) are **bit-for-bit identical** between the freshly reproduced run and the committed metrics file. This is a strong, positive reproducibility result — the checkpoint on disk genuinely is the one that produced the committed numbers, on the same test split.

**One flagged discrepancy:** `pr_auc` differs in the 4th decimal place — reproduced `0.9602` vs committed `0.9601`. This is consistent with a floating-point ordering/batching difference in `average_precision_score` (this reproduction ran inference in batches of 32 with dynamic padding, rather than the Trainer's internal batching at training time) and is **not evidence of a different model or a different test set** — the identical confusion matrix at the 0.5 threshold rules that out. Reported here rather than silently rounded away, per the instruction to flag any discrepancy exactly as found.

The overall benchmark numbers quoted in the Week 1 task brief (precision 0.9625, recall 0.9620, F1 0.9623, F2 0.9621, ROC-AUC 0.9703, PR-AUC 0.9601, Brier 0.0312) match the committed file exactly.

**These are SYNTHETIC-DATA metrics from a 5,000-row held-out split of the 25,000-row generated corpus. They are internal consistency validation only and must not be presented as OIL India performance at any point in Phases 2-8.**

### 20. Git status (repeated for completeness, see §0)

Already captured above — no changes were made to tracked files during Phase 1.

---

## Summary of notable findings for Phase 2+ planning

- The live default model is the fine-tuned DistilBERT, contingent entirely on the gitignored checkpoint being present locally — a fresh clone silently falls back to `baseline2` (TF-IDF+LogReg) with no error, which is by design but worth remembering when comparing "Sentinel" behavior across machines.
- All extraction (activity/hazard/exposure/barrier/location) is **phrase-list / regex based**, not learned — `evidence_extractor.py`'s `BARRIER_TERMS`, `EXPOSURE_KEYWORD_GROUPS`, `NO_EXPOSURE_PHRASES`, `EXPLICIT_ABSENCE_PHRASES`, `UNCERTAINTY_PHRASES` are all hardcoded English phrase lists tuned against the synthetic generator's own vocabulary. This is the single most likely source of generalization failure on genuinely external text and should be the primary focus of Phase 5/6 error analysis.
- The routing weights (`W_ENERGY`/`W_BARRIER`/`W_EXPOSURE`) and confidence thresholds (0.75/0.25) are explicitly self-flagged in the code as uncalibrated placeholders awaiting real evaluation data — Week 1's external evaluation is precisely the first opportunity to test them against something other than synthetic data.
- Dead code exists in `pipeline.py` (`_extract_heuristic_fields`) that reads two ontology keys that don't exist; it has no live effect today but should not be mistaken for an active code path during Phase 5/6/7 investigation.
- The task brief's "3,000 reports" figure is stale; current corpus is 25,000 rows / 5,000-row test split — external evaluation set sizing in Phase 4 should be judged against Sentinel's actual training scale, not the stale figure.
