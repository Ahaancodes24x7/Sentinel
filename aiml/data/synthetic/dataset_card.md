# Synthetic UA/UC Dataset Card

**THIS IS NOT OIL INDIA DATA.** Every row carries `source="synthetic"`.
The corpus exists so the pipeline can be built and measured before any
real OIL HSSE export is available. Metrics computed on it are *internal
consistency validation*, not production validation.

## Provenance

- Rows: **25,000** (requested 25,000)
- Seed: `42` (fully reproducible)
- Window: 12 months ending 2026-09-01
- Gold NER spans: **118,443** across 5 entity types
  (ACTIVITY, HAZARD, BARRIER, EXPOSURE, LOCATION)

## Labelling logic (EEI SCL Model)

```
sif_potential = high_energy(energy_type)
                AND exposure != no_exposure
                AND NOT (barrier confirmed AND barrier is a DIRECT control)
```

The label is **independent of the stated outcome**. A no-injury near-miss
with an absent barrier is positive; a first-aid case behind a verified
mechanical barrier is negative. A confirmed *administrative* control
(permit, journey plan) does not clear a high-energy exposure the way a
confirmed *engineering* control does — the SCL direct-control test.

- Positive rate (as labelled, incl. 3% injected ambiguity): **43.2%**
- Positive rate (noise-free ground truth): **42.8%**
- `sif_potential_truth` is retained so label-noise robustness can be measured.

## Injected realism

- Abbreviation substitution (PTW, LOTO, JSA, H2S, SIMOPS)
- Field typos (`confimed`, `maintainance`, `wielding`, `isolaton`, ...)
- Code-mixed Hindi/Assamese-influenced phrasing appended to ~35% of noisy rows
- Terse fragment reports (~16%)
- Inconsistent casing, trailing shift-log notes
- ~35% of rows are left clean, mirroring a mix of careful and hurried reporters

## Planted structure (so pattern discovery has real signal)

| pattern_id | kind | site | barrier failure | n |
|---|---|---|---|---|
| `p_isolation_handover` | established | Rig 7 | stored/electrical energy / uncertain | 260 |
| `p_isolation_maint` | established | Plant C | stored/electrical energy / uncertain | 220 |
| `p_lift_zone` | established | Rig 4 | gravitational (suspended load) / explicitly_absent | 190 |
| `p_sis_bypass` | emerging | Plant D | defeated safety system / explicitly_absent | 150 |
| `p_gastest_stale` | emerging | Terminal A | atmospheric/asphyxiation / uncertain | 120 |
| `p_pressure_rare` | sporadic_high_severity | Pipeline Section 9 | pressure/hydraulic energy / explicitly_absent | 14 |
| `p_radiography_rare` | sporadic_high_severity | Field Station 5 | radiation (NORM/radiography) / explicitly_absent | 9 |

`emerging` patterns are concentrated in the final ~25% of the timeline so the
CUSUM/EWMA early-warning layer has a genuine step change to detect.
`sporadic_high_severity` patterns are deliberately too small to cluster as
'recurring' — they must surface through the outlier view instead.

## Distribution

### Sites

| site | reports |
|---|---|
| Plant C | 4,717 |
| Plant D | 3,140 |
| Terminal A | 3,056 |
| Workshop Central | 2,351 |
| Rig 12 | 2,276 |
| Rig 4 | 2,146 |
| Rig 7 | 1,597 |
| Field Station 2 | 1,459 |
| Well Site F | 1,180 |
| Pipeline Section 9 | 1,036 |
| Well Site B | 1,026 |
| Field Station 5 | 1,016 |

### Energy types

| energy type | reports |
|---|---|
| pressure/hydraulic energy | 3,704 |
| stored/electrical energy | 2,901 |
| low-energy/ergonomic | 2,770 |
| gravitational (suspended load) | 2,322 |
| mechanical/rotating equipment | 2,123 |
| flammable/explosive atmosphere | 1,830 |
| kinetic (line of fire) | 1,730 |
| defeated safety system | 1,514 |
| vehicular/motion | 1,459 |
| atmospheric/asphyxiation | 1,250 |
| fall from height | 1,131 |
| chemical/toxic exposure | 776 |
| radiation (NORM/radiography) | 772 |
| thermal (hot work) | 718 |

### Life-Saving Rule tags (positives only)

| LSR | reports |
|---|---|
| Energy Isolation | 2,990 |
| Line of Fire | 1,577 |
| Hot Work | 1,226 |
| Work Authorisation | 1,171 |
| Safe Mechanical Lifting | 1,064 |
| Driving | 1,011 |
| Bypassing Safety Controls | 692 |
| Confined Space | 614 |
| Working at Height | 457 |

## Known limitations

- Generated from a finite phrase bank; a model can overfit the generator.
- Real reports contain equipment tags, org-specific jargon and narrative
  digressions this generator does not reproduce.
- Real validation requires an OIL SME-reviewed gold set on real exports.
