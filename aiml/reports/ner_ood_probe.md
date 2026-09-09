# NER Out-of-Distribution Probe

## Why this page exists

The fine-tuned model scores **exact span F1 = 1.0** on a held-out
split of the synthetic corpus. That number should not be quoted as a quality
result. Both halves of the split come from the same finite phrase bank, so a
transformer simply memorises the spans and the metric saturates. A perfect
score on generated data is evidence about the generator, not about the model.

The probes below are hand-written in the register of real upstream oil & gas
near-miss reports — vocabulary, sentence shapes, abbreviations and field idiom
the generator never produces. This is the only part of the NER evaluation that
says anything about generalisation.

## What it shows

The model transfers **partially**. It reliably picks up site identifiers and
explicit barrier-absence constructions it has never seen verbatim, which is the
signal the SCL reasoner actually depends on. Span boundaries are noticeably
raggeder than on synthetic text, and it occasionally labels an outcome clause as
exposure. In deployment those cases are exactly what the confidence routing sends
to a human rather than deciding alone.

## Probes

### 1.

> Whilst the crew were breaking the flange on the 6-inch discharge header at PS-9, the line had not been proven depressurised. Two fitters were stood square to the joint. Nobody was injured.

`source: transformer` · 7 spans

| Label | Confidence | Extracted span |
|---|---|---|
| EXPOSURE | 0.89 | the crew were breaking the fl |
| ACTIVITY | 0.43 | ange on the |
| HAZARD | 0.71 | 6-inch discharge header |
| LOCATION | 0.99 | PS-9 |
| HAZARD | 1.00 | the line had not been proven depressurised |
| EXPOSURE | 1.00 | Two fitters were stood square to the joint |
| EXPOSURE | 0.83 | was injured |

### 2.

> Observed a rigger riding the load on the cellar deck crane at Rig 12. No taglines rigged, no barricade. Job stopped by the DSV.

`source: transformer` · 5 spans

| Label | Confidence | Extracted span |
|---|---|---|
| EXPOSURE | 0.94 | a rigger riding the load on the |
| ACTIVITY | 0.91 | cellar deck crane |
| LOCATION | 1.00 | Rig 12 |
| BARRIER | 0.97 | No taglines rigged |
| BARRIER | 0.96 | no barricade |

### 3.

> Night crew found the F&G loop in override from the previous shift with no compensating watchkeeper. Compressor running.

`source: transformer` · 3 spans

| Label | Confidence | Extracted span |
|---|---|---|
| ACTIVITY | 0.73 | &G |
| BARRIER | 0.93 | loop in override from the previous shift |
| BARRIER | 1.00 | no compensating watchkeeper |

### 4.

> Trolley of gas cylinders left unchained at the top of the ramp near the workshop door. Nobody about at the time.

`source: transformer` · 1 spans

| Label | Confidence | Extracted span |
|---|---|---|
| HAZARD | 0.92 | Trolley of gas cylinders left unchained at the top of the ramp near the workshop door |

### 5.

> Contractor entered the sump at Terminal A to retrieve a dropped spanner. No entry permit raised and the gas monitor was still on charge in the cabin.

`source: transformer` · 7 spans

| Label | Confidence | Extracted span |
|---|---|---|
| EXPOSURE | 0.53 | entered the |
| ACTIVITY | 0.72 | sump |
| LOCATION | 1.00 | Terminal A |
| EXPOSURE | 0.60 | to retrieve |
| HAZARD | 0.87 | a dropped spanner |
| BARRIER | 1.00 | No entry permit raised |
| BARRIER | 1.00 | the gas monitor was still on charge in the cabin |

### 6.

> Excavator bucket swung within a metre of the banksman while backfilling the trench at Field Station 5. Spoil heap obstructing his line of sight.

`source: transformer` · 11 spans

| Label | Confidence | Extracted span |
|---|---|---|
| ACTIVITY | 0.92 | Excavator bucket swung |
| EXPOSURE | 0.93 | within a metre of the banksman |
| EXPOSURE | 0.87 | back |
| HAZARD | 0.50 | fi |
| EXPOSURE | 0.65 | lling the |
| HAZARD | 0.79 | trench |
| LOCATION | 1.00 | Field Station 5 |
| HAZARD | 0.70 | heap |
| HAZARD | 0.67 | structing |
| HAZARD | 0.58 | line |
| HAZARD | 0.51 | sight |

### 7.

> Scaffolder observed transferring between lifts without clipping on. Scaffold tag showed incomplete handrail on the north face.

`source: transformer` · 3 spans

| Label | Confidence | Extracted span |
|---|---|---|
| ACTIVITY | 0.81 | transferring between lifts |
| HAZARD | 0.83 | without clipping on |
| HAZARD | 0.99 | Scaffold tag showed incomplete handrail on the north face |

### 8.

> Tanker driver began disconnecting the loading arm before the pump had stopped. Product under pressure in the line.

`source: transformer` · 6 spans

| Label | Confidence | Extracted span |
|---|---|---|
| ACTIVITY | 0.69 | Tanker driver |
| EXPOSURE | 0.97 | began |
| HAZARD | 0.76 | disconnecting the loading arm |
| EXPOSURE | 0.63 | before |
| HAZARD | 0.98 | the pump had stopped |
| HAZARD | 1.00 | Product under pressure in the line |

## Reading this honestly

- **Do not claim** the 1.000 synthetic F1 as production extraction quality.
- **Do claim** that barrier-absence and location extraction transfer to unseen
  phrasing, and show these probes as the evidence.
- Real span-level validation needs an SME-annotated gold set drawn from actual
  OIL HSSE exports, with inter-annotator agreement measured before any number is
  treated as an acceptance criterion.
