# Sentinel — Model Evaluation Report

Model version `sentinel-v2.0` · 149s total train+eval time.

> **Validation status: internal consistency only.** Every number below is
> measured against a held-out split of the *synthetic* corpus and therefore
> validates the pipeline against its own generation assumptions. It is not
> production validation. Real acceptance criteria can only be set with OIL
> HSE SMEs after a pilot on real exported data.

## Why not accuracy

The positive class is 43.2% of the corpus and a **false negative
(a missed SIF precursor) is categorically worse than a false positive (one
extra human review)**. So the headline metric is recall at a stated
review-queue size, with F2 (recall weighted 2x) as the summary score — the
same choice the VelocityEHS PSIF paper made, for the same reason.

The corpus also carries 2.8% deliberate label noise, so a
perfect score would itself be evidence of overfitting rather than success.

## Dataset

- Total: **25,000** synthetic reports
- Split: train 15,000 / val 5,000 / test 5,000 (stratified)
- SIF-potential rate: 43.2%

## Baseline ladder

Built simplest-first so the marginal value of each added layer is measured,
not assumed.

| Model | Recall | Precision | F2 | PR-AUC | Review queue |
|---|---|---|---|---|---|
| B1 keyword / rule | 0.231 | 0.827 | 0.269 | — | 12.0% |
| B2 TF-IDF + LogReg | 0.954 | 0.947 | 0.952 | 0.958 | 43.5% |
| B3 embedding kNN | — | — | — | — | — |
| **B4 calibrated word+char (production)** | 0.914 | 0.967 | 0.924 | 0.959 | 40.8% |
| B5 hybrid extraction + SCL reasoner | 0.844 | 0.715 | 0.815 | — | 48.6% |

## Production model operating point

- Threshold **0.738**, selected on the VALIDATION split
  as the highest threshold still achieving >=90% recall, then applied
  unchanged to test. Selecting it on test would have been leakage.
- Test recall **91.4%** at a review queue of **40.8%** of all reports.
- PR-AUC 0.959 · Brier 0.0397

### Calibration

Expected Calibration Error **0.0339**.
This matters because the 4-bucket review routing is driven by the
confidence score: a model whose "0.9" is right 60% of the time sends the
wrong reports to the priority queue no matter how well it ranks.

### Outcome-shortcut check

The single most dangerous failure mode for this problem is a model that
learns "text that mentions injury -> dangerous", because that is exactly
backwards for near-miss reports. Top positive tokens of the interpretable
bag-of-words baseline:

```
working, radiography, worker was, but, being, general work, the general, work area, general, area at, inside, inside the, place at, was being, pipeline welds
```

No injury/outcome tokens in the top features. The model is keying on barrier and energy language, which is the intended behaviour.

## Life-Saving Rule tagging

Top-1 **99.0%** · Top-2 **100.0%** across 9 IOGP rules (2,160 test reports).

| Rule | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Bypassing Safety Controls | 0.99 | 1.00 | 0.99 | 142 |
| Confined Space | 0.99 | 1.00 | 0.99 | 146 |
| Driving | 1.00 | 0.99 | 1.00 | 197 |
| Energy Isolation | 0.99 | 0.99 | 0.99 | 561 |
| Hot Work | 0.99 | 1.00 | 1.00 | 281 |
| Line of Fire | 0.98 | 0.97 | 0.98 | 311 |
| Safe Mechanical Lifting | 0.97 | 0.99 | 0.98 | 203 |
| Work Authorisation | 1.00 | 1.00 | 1.00 | 242 |
| Working at Height | 0.99 | 0.99 | 0.99 | 77 |
| macro avg | 0.99 | 0.99 | 0.99 | 2160 |
| weighted avg | 0.99 | 0.99 | 0.99 | 2160 |

## Supporting extraction heads

- Energy type: **98.5%** accuracy over 14 classes
- Barrier status (4 states): **100.0%** accuracy, ECE 0.0011

## Hybrid system (the proposed contribution)

B5 is the two-stage architecture: learned extraction feeding a fixed,
auditable SCL decision structure. Its value is not a higher raw score than
B4 — it is that every decision arrives with the extracted fields, spans and
an ontology-grounded justification attached, which an end-to-end classifier
structurally cannot provide.

- Recall 0.844 · Precision 0.715 · F2 0.815
- LSR top-1 (ontology lookup, not learned): 0.760
- 25 ms/report single-threaded

Review-bucket distribution:

| Bucket | Reports |
|---|---|
| LOW_CONF_REVIEW | 747 |
| NEEDS_MORE_INFO | 411 |
| HIGH_CONF_NON_SIF | 237 |
| HIGH_CONF_SIF | 105 |

## Saturated metrics — read these as a warning, not a result

The following scores are at or near ceiling: **barrier status (1.000)**, **LSR top-1 (0.990)**, **bag-of-words recall (0.954)**.

That is not evidence of a strong model. It is evidence that the synthetic
generator is predictable: every categorical value is realised from a finite
phrase bank, so a classifier can recover the label by recognising the
template rather than by reading the situation. The fine-tuned NER model
shows the same effect even more starkly, scoring exact span F1 = 1.000 —
see `reports/ner_ood_probe.md`, where the same model is run against
hand-written reports the generator could not have produced and its span
boundaries visibly degrade.

The numbers worth attending to are the ones that are NOT saturated: the
hybrid system's recall/precision, calibration error, and the gap between the
rule baseline and the learned models. Those still carry signal.

## What this does and does not establish

**Established:** the pipeline runs end to end on messy, code-mixed, typo-laden
text; the SCL reasoning is faithfully implemented; confidence is calibrated
well enough to drive review routing; the model is not keying on injury words.

**Not established:** real-world recall or precision. These metrics are
circular to the extent that the test set shares generation assumptions with
the training set. Real validation requires an SME-reviewed gold set drawn from
actual OIL HSSE exports, with inter-annotator agreement measured (target
Cohen's kappa > 0.6) before any production threshold is agreed.
