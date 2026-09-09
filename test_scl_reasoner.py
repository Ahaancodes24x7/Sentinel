"""Regression tests for scl_reasoner.py — run before ever treating this
module as locked/production."""

from scl_reasoner import reason

PASSED, FAILED = 0, 0


def check(name, cond):
    global PASSED, FAILED
    status = "PASS" if cond else "FAIL"
    if cond:
        PASSED += 1
    else:
        FAILED += 1
    print(f"[{status}] {name}")


# 1. Near-miss preservation: no injury + hazardous exposure + gap = still SIF
r1 = reason(
    "During electrical panel work at Well Site B, a technician was inside the equipment "
    "when work commenced. No isolation was mentioned in the report. No injury occurred."
)
check("near-miss preservation (no injury, but flagged True)", r1.sif_potential is True)
check("near-miss -> HIGH_CONF_SIF for explicit absence", r1.bucket == "HIGH_CONF_SIF")

# 2. not_mentioned -> NEEDS_MORE_INFO, never auto-flagged True or False
r2 = reason("Routine patrol at Terminal A. No personnel were in the vicinity. No injury occurred.")
check("not_mentioned barrier -> sif_potential is None (not True, not False)", r2.sif_potential is None)
check("not_mentioned barrier -> NEEDS_MORE_INFO bucket", r2.bucket == "NEEDS_MORE_INFO")

# 3. Explicit no-exposure correctly suppresses a flag even with a real hazard+gap
r3 = reason(
    "During confined space entry at Plant C, no isolation was mentioned in the report. "
    "No personnel were in the vicinity at the time."
)
check("no_exposure suppresses sif_potential even with barrier gap", r3.sif_potential is False)

# 4. Confirmed barrier -> never flagged regardless of exposure
r4 = reason(
    "During hot work / welding at Rig 4, a worker was standing within the immediate hazard zone. "
    "Isolation was verified and tagged before work began."
)
check("confirmed barrier -> sif_potential False despite direct exposure", r4.sif_potential is False)

# 5. Evidence spans point into the RAW text, not a preprocessed/altered string
r5 = reason("LOTO tag not confimed. Mazdoor ko turant hataya gaya at Rig 7.")
# (raw, unpreprocessed — deliberately messy/abbreviated/code-mixed input)
check("evidence dict is present for raw messy input", isinstance(r5.evidence, dict))

# 6. Provenance is always explicit
check("hazard_gate_source always stated", r1.hazard_gate_source == "rule_based_evidence_extractor_v1")

# 7. bucket is always one of the 4 valid values, on all above
for i, r in enumerate([r1, r2, r3, r4], start=1):
    check(f"result {i} bucket is valid", r.bucket in {"HIGH_CONF_SIF", "LOW_CONF_REVIEW", "HIGH_CONF_NON_SIF", "NEEDS_MORE_INFO"})

# 8. Informational energy_type never overrides the rule-based gate's False
r8 = reason(
    "During routine equipment inspection at Plant C, isolation was verified and tagged before work began.",
    predicted_energy_type="thermal (hot work)",  # a high-energy label, but should NOT flip the gate
)
check("predicted_energy_type never overrides the rule-based gate", r8.sif_potential is False)

print(f"\n{PASSED} passed, {FAILED} failed out of {PASSED + FAILED}")
if FAILED:
    raise SystemExit(1)
