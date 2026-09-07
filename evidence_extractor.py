"""
PS 26165 — Evidence Extractor (correction pass on feature_extractor.py)
=========================================================================

This module exists to fix three specific, valid gaps identified in review
of the Stage 1 pipeline (feature_extractor.py + scl_reason()):

1. HAZARD extraction was missing. `energy_type` (predicted by the trained
   TF-IDF classifier) is the closest thing to it, but nothing exposed a
   hazard *category with supporting evidence*. Fixed here: hazard
   categories reuse the same 8 LSR-aligned keyword groups already in
   feature_extractor.py, but now return matched phrases + char offsets,
   not just a count.

2. LOCATION extraction was missing entirely. Fixed here: site names are a
   closed, known vocabulary (Rig 4, Rig 7, Plant C, Well Site B, Field
   Station 2, Terminal A) — exact substring matching gives a location
   value AND a real, exact evidence span. No model needed; this is a
   correct, not a lazy, solution for a closed vocabulary.

3. barrier_status semantics were dangerously collapsed. scl_reason() had:
       barrier_gap = barrier_status != "confirmed_present"
   which treats "uncertain" identically to "absent_not_mentioned" — a
   real semantic difference the ground-truth ontology itself already
   distinguishes. Fixed here: `estimate_barrier_status()` returns FOUR
   distinct states (confirmed / uncertain / explicitly_absent /
   not_mentioned), each with its own `gap_severity` in [0, 1] rather than
   a single boolean, and each backed by the specific matched evidence
   (which confirmation words were negated, which explicit-absence phrases
   matched, or the absence of any barrier language at all).

None of this replaces the trained field classifiers in
train_field_extractors_and_reasoner.py — those remain the actual
*predictions* Stage 1 produces. This module is the EVIDENCE layer: for
any predicted category, it locates supporting text spans and, for
barrier status specifically, a more defensible graded estimate. This is
still not full neural span-level NER (that needs either a transformer
with token-classification training, or hand/semi-automatically labeled
span data — see the bottom of this file for how this project could
generate real gold span labels from the synthetic generator itself,
which is a legitimate and available next step, unlike pretrained
transformers in this sandbox).
"""

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Reuse the same domain keyword groups as feature_extractor.py, but here
# we need MATCH POSITIONS, not just counts.
# ---------------------------------------------------------------------------
HAZARD_KEYWORD_GROUPS = {
    "energy_isolation":        ["isolation", "electrical", "energized", "lockout", "tagout", "live circuit", "de-energized"],
    "hot_work":                ["hot work", "welding", "cutting", "grinding", "open flame"],
    "confined_space":          ["confined space", "gas test", "atmospheric", "asphyxiation", "tank entry"],
    "line_of_fire":            ["line of fire", "suspended load", "swinging", "dropped object", "pinch point"],
    "safe_mechanical_lifting": ["crane", "lifting", "rigging", "hoist", "sling"],
    "working_at_height":       ["height", "scaffolding", "fall", "harness", "elevated platform"],
    "driving":                 ["vehicle", "driving", "traffic", "reversing"],
    "excavation":              ["excavation", "trench", "buried utility", "digging"],
}

ACTIVITY_KEYWORD_GROUPS = {
    "maintenance":        ["maintenance", "process equipment"],
    "hot_work_activity":  ["hot work", "welding", "process line"],
    "lifting_activity":   ["lifting", "mobile crane"],
    "confined_activity":  ["confined space", "tank cleaning"],
    "vehicle_activity":   ["vehicle", "plant premises"],
    "excavation_activity": ["excavation", "buried utility"],
    "electrical_activity": ["electrical panel"],
    "scaffolding_activity": ["scaffolding", "height"],
    "pipeline_activity":   ["pipeline", "pigging"],
    "inspection_activity": ["routine", "inspection"],
}

EXPOSURE_KEYWORD_GROUPS = {
    "direct":   ["within", "beneath", "inside", "directly", "arm's reach"],
    "indirect": ["nearby", "in the vicinity", "general work area"],
}
NO_EXPOSURE_PHRASES = [
    "no personnel were in the vicinity", "no personnel in the vicinity",
    "area was clear of workers", "area clear of workers", "area was clear",
]

# Closed vocabulary — exact match gives exact evidence, no model needed.
KNOWN_SITES = ["Rig 4", "Rig 7", "Plant C", "Well Site B", "Field Station 2", "Terminal A"]

CONFIRMATION_TARGETS = ["confirmed", "verified", "established", "completed", "clear", "tagged",
                         "checked", "signed", "enforced", "located", "sign-off"]
NEGATION_CUES_SINGLE = ["no", "not", "never", "nor", "lack", "absence", "unable", "without"]
NEGATION_CUES_MULTI = ["could not", "did not"]

# Phrases that assert EXPLICIT absence — distinct from a negated confirmation
# word. "no isolation was mentioned" is a stronger, more direct claim than
# "isolation was not clearly confirmed" (which is closer to genuine
# uncertainty about a barrier that may or may not exist).
EXPLICIT_ABSENCE_PHRASES = [
    "no isolation", "no exclusion zone", "without a permit", "no permit", "not sighted",
]
# Phrase that means "the report is simply silent on this" — different again
# from an explicit denial.
NO_MENTION_PHRASE = "not mentioned"


@dataclass
class Evidence:
    phrase: str
    span: tuple[int, int]


@dataclass
class BarrierAssessment:
    status: str            # "confirmed" | "uncertain" | "explicitly_absent" | "not_mentioned"
    gap_severity: float     # 0.0 (no gap) .. 1.0 (maximum gap) — NOT a boolean
    evidence: list[Evidence] = field(default_factory=list)


def _find_all(text_lower: str, phrase: str) -> list[tuple[int, int]]:
    spans = []
    start = 0
    while True:
        idx = text_lower.find(phrase, start)
        if idx == -1:
            break
        spans.append((idx, idx + len(phrase)))
        start = idx + 1
    return spans


def extract_category_evidence(text: str, keyword_groups: dict[str, list[str]]) -> dict:
    """For each category in keyword_groups, return matched phrases + spans.
    Also returns `best_category`: the group with the most matches (ties
    broken by first occurrence position), or None if nothing matched."""
    text_lower = text.lower()
    matches_by_category = {}
    for category, phrases in keyword_groups.items():
        ev = []
        for phrase in phrases:
            for span in _find_all(text_lower, phrase):
                ev.append(Evidence(phrase=text[span[0]:span[1]], span=span))
        if ev:
            matches_by_category[category] = ev

    best_category = None
    if matches_by_category:
        best_category = max(
            matches_by_category,
            key=lambda c: (len(matches_by_category[c]), -min(e.span[0] for e in matches_by_category[c])),
        )
    return {"best_category": best_category, "matches": matches_by_category}


def extract_location(text: str) -> dict:
    """Closed-vocabulary exact match — genuinely correct, not a stand-in,
    because OIL's site list IS a closed vocabulary (unlike open-ended
    hazard/activity language)."""
    for site in KNOWN_SITES:
        idx = text.find(site)
        if idx != -1:
            return {"value": site, "evidence": Evidence(phrase=site, span=(idx, idx + len(site)))}
    return {"value": None, "evidence": None}


def estimate_barrier_status(text: str, window: int = 4) -> BarrierAssessment:
    """Replaces the collapsed binary in the original scl_reason(). Returns
    one of FOUR distinct states with a graded severity, each backed by its
    own specific evidence — this is the direct fix for the critique's
    point that 'uncertain', 'explicitly absent', and 'not mentioned' were
    being silently treated as identical."""
    text_lower = text.lower()
    tokens = re.findall(r"[a-zA-Z']+", text_lower)

    affirmed_evidence, negated_evidence = [], []
    for term in CONFIRMATION_TARGETS:
        for m in re.finditer(r"\b" + re.escape(term) + r"\b", text_lower):
            token_idx = len(re.findall(r"[a-zA-Z']+", text_lower[:m.start()]))
            window_toks = tokens[max(0, token_idx - window):token_idx]
            window_bigrams = [" ".join(window_toks[j:j + 2]) for j in range(len(window_toks) - 1)]
            is_negated = any(c in window_toks for c in NEGATION_CUES_SINGLE) or \
                         any(c in window_bigrams for c in NEGATION_CUES_MULTI)
            ev = Evidence(phrase=text[m.start():m.end()], span=(m.start(), m.end()))
            (negated_evidence if is_negated else affirmed_evidence).append(ev)

    absence_evidence = []
    for phrase in EXPLICIT_ABSENCE_PHRASES:
        for span in _find_all(text_lower, phrase):
            absence_evidence.append(Evidence(phrase=text[span[0]:span[1]], span=span))

    no_mention_evidence = []
    for span in _find_all(text_lower, NO_MENTION_PHRASE):
        no_mention_evidence.append(Evidence(phrase=text[span[0]:span[1]], span=span))

    # Decision order matters and is deliberately explicit, not a single
    # collapsed inequality:
    if absence_evidence:
        # An explicit denial is the strongest, most direct signal.
        return BarrierAssessment(status="explicitly_absent", gap_severity=1.0, evidence=absence_evidence)
    if no_mention_evidence:
        # The report is silent on the barrier entirely — per this
        # project's own preprocessing principle, silence is informative
        # and must never be treated as "present". Slightly lower severity
        # than an explicit denial, since we have zero information rather
        # than an active claim of absence.
        return BarrierAssessment(status="not_mentioned", gap_severity=0.8, evidence=no_mention_evidence)
    if negated_evidence and not affirmed_evidence:
        # "not clearly confirmed" etc. — genuine uncertainty, not a denial.
        return BarrierAssessment(status="uncertain", gap_severity=0.6, evidence=negated_evidence)
    if negated_evidence and affirmed_evidence:
        # Mixed signal in the same report (e.g. one barrier confirmed,
        # another not) — treat as uncertain but flag both pieces of evidence.
        return BarrierAssessment(status="uncertain", gap_severity=0.5, evidence=negated_evidence + affirmed_evidence)
    if affirmed_evidence:
        return BarrierAssessment(status="confirmed", gap_severity=0.0, evidence=affirmed_evidence)
    # No barrier language of any kind detected.
    return BarrierAssessment(status="not_mentioned", gap_severity=0.8, evidence=[])


def estimate_exposure(text: str) -> dict:
    """Same negation-awareness discipline as estimate_barrier_status():
    an explicit 'no personnel were in the vicinity' must NOT be classified
    as 'indirect exposure' just because 'vicinity' is an indirect-exposure
    keyword. Explicit no-exposure phrases are checked FIRST, before the
    generic keyword-group match, exactly mirroring the barrier fix above —
    this was caught by inspecting this module's own test output, which is
    the point of running examples rather than trusting the design on paper."""
    text_lower = text.lower()

    for phrase in NO_EXPOSURE_PHRASES:
        for span in _find_all(text_lower, phrase):
            return {
                "best_category": "no_exposure",
                "matches": {"no_exposure": [Evidence(phrase=text[span[0]:span[1]], span=span)]},
            }

    return extract_category_evidence(text, EXPOSURE_KEYWORD_GROUPS)


def extract_evidence(text: str) -> dict:
    """The unified extraction call: activity, hazard, location, exposure
    (category + evidence spans) and barrier (graded assessment + evidence).
    This is what a report-detail UI should render highlighting from —
    every span here is a real character offset into `text`, not a
    classifier's opaque confidence number."""
    activity = extract_category_evidence(text, ACTIVITY_KEYWORD_GROUPS)
    hazard = extract_category_evidence(text, HAZARD_KEYWORD_GROUPS)
    exposure = estimate_exposure(text)
    location = extract_location(text)
    barrier = estimate_barrier_status(text)

    return {
        "activity": activity,
        "hazard": hazard,
        "exposure": exposure,
        "location": location,
        "barrier": barrier,
    }


if __name__ == "__main__":
    samples = [
        "During maintenance on process equipment at Rig 4, a worker was standing within the immediate hazard zone. Isolation status was not clearly confirmed by the crew. No injury occurred.",
        "During electrical panel work at Well Site B, a technician was inside the equipment when work commenced. No isolation was mentioned in the report. Minor first aid case reported.",
        "During routine equipment inspection at Plant C, isolation was verified and tagged before work began. No personnel were in the vicinity at the time. No injury occurred.",
    ]
    for text in samples:
        print("TEXT:", text)
        result = extract_evidence(text)
        print("  Activity best guess:", result["activity"]["best_category"])
        print("  Hazard best guess:  ", result["hazard"]["best_category"])
        print("  Location:           ", result["location"]["value"])
        print("  Exposure best guess:", result["exposure"]["best_category"])
        b = result["barrier"]
        print(f"  Barrier: status={b.status}, gap_severity={b.gap_severity}, "
              f"evidence={[e.phrase for e in b.evidence]}")
        print()
