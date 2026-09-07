"""Stage 1 Evidence Extractor for SIF Precursor Detection.

Extracts structured domain evidence directly from raw report text:
- Activity (phrase + exact raw span)
- Hazard (LSR-aligned keyword groups + exact raw spans)
- Exposure (negation-aware: explicit no-exposure phrases prioritized over proximity cues)
- Barrier & Barrier Status (4 distinct states with graded gap severity):
    * confirmed: gap_severity = 0.0
    * uncertain: gap_severity = 0.6
    * explicitly_absent: gap_severity = 1.0
    * not_mentioned: gap_severity = None (review-required / insufficient info)
- Location (prototype/synthetic site vocabulary + exact raw span)

IMPORTANT: All character spans [start_char, end_char] reference the raw un-preprocessed
report text to guarantee coordinate invariance for UI highlighting.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Prototype / Synthetic Site Vocabulary
# ---------------------------------------------------------------------------
PROTOTYPE_SITES = [
    "Rig 4", "Rig 7", "Plant C", "Well Site B", "Field Station 2", "Terminal A"
]

# ---------------------------------------------------------------------------
# Hazard Keyword Groups (8 LSR-aligned categories)
# ---------------------------------------------------------------------------
HAZARD_KEYWORD_GROUPS = {
    "energy_isolation": [
        "isolation", "electrical", "energized", "lockout", "tagout",
        "live circuit", "de-energized", "loto", "switchboard", "breaker"
    ],
    "hot_work": [
        "hot work", "welding", "cutting", "grinding", "open flame", "torch"
    ],
    "confined_space": [
        "confined space", "gas test", "atmospheric", "asphyxiation",
        "tank entry", "vessel entry", "toxic gas", "oxygen deficiency"
    ],
    "line_of_fire": [
        "line of fire", "suspended load", "swinging", "dropped object",
        "pinch point", "high pressure line", "recoil"
    ],
    "safe_mechanical_lifting": [
        "crane", "lifting", "rigging", "hoist", "sling", "shackle", "winch"
    ],
    "working_at_height": [
        "height", "scaffolding", "fall", "harness", "elevated platform",
        "ladder", "manlift", "fall arrest"
    ],
    "driving": [
        "vehicle", "driving", "traffic", "reversing", "forklift", "collision"
    ],
    "excavation": [
        "excavation", "trench", "buried utility", "digging", "cave-in", "shoring"
    ],
}

# ---------------------------------------------------------------------------
# Activity Keyword Groups
# ---------------------------------------------------------------------------
ACTIVITY_KEYWORD_GROUPS = {
    "maintenance": ["maintenance", "process equipment", "servicing", "overhaul"],
    "hot_work_activity": ["hot work", "welding", "process line", "pipe fabrication"],
    "lifting_activity": ["lifting operation", "mobile crane", "lifting", "rigging operation"],
    "confined_activity": ["confined space entry", "tank cleaning", "vessel inspection"],
    "vehicle_activity": ["vehicle movement", "plant premises", "driving", "transportation"],
    "excavation_activity": ["excavation", "buried utility line", "trenching"],
    "electrical_activity": ["electrical panel", "substation", "switchgear", "transformer"],
    "scaffolding_activity": ["scaffolding erection", "scaffold dismantling", "height work"],
    "pipeline_activity": ["pipeline pigging", "pigging operation", "pipeline maintenance"],
    "inspection_activity": ["routine equipment inspection", "routine walk-around", "routine inspection"],
}

# ---------------------------------------------------------------------------
# Exposure Keyword & Phrase Groups
# ---------------------------------------------------------------------------
EXPOSURE_KEYWORD_GROUPS = {
    "direct_proximity": [
        "within the immediate hazard zone", "directly beneath", "directly under",
        "within arm's reach", "inside the equipment", "standing within",
        "in the line of fire", "in direct path", "crew entered", "vessel entry",
        "tank entry", "inside the vessel", "worker entered", "personnel entered",
        "entered the vessel", "entered the confined space"
    ],
    "indirect_proximity": [
        "nearby", "in the vicinity", "general work area", "adjacent area",
        "around the perimeter"
    ],
}

NO_EXPOSURE_PHRASES = [
    "no personnel were in the vicinity",
    "no personnel in the vicinity",
    "area was clear of workers",
    "area clear of workers",
    "area was clear",
    "area clear",
    "no workers were present",
    "no personnel present",
    "all personnel were evacuated",
    "all workers evacuated",
    "barricaded with no entry",
]

# ---------------------------------------------------------------------------
# Barrier Status Cues
# ---------------------------------------------------------------------------
CONFIRMATION_TARGETS = [
    "confirmed", "verified", "re-verified", "reverified", "established",
    "completed", "clear", "tagged", "checked", "rechecked", "signed",
    "enforced", "located", "sign-off", "secured", "tested safe"
]

NEGATION_CUES_SINGLE = ["no", "not", "never", "nor", "lack", "absence", "unable", "without"]
NEGATION_CUES_MULTI = ["could not", "did not", "was not", "were not", "failed to"]

EXPLICIT_ABSENCE_PHRASES = [
    "no isolation", "no exclusion zone", "without a permit", "no permit",
    "not sighted", "isolation not done", "not isolated", "lockout not applied",
    "tagout not applied", "no gas test", "gas test not done", "no harness",
    "without harness", "unsecured", "not barricaded"
]

NO_MENTION_PHRASES = [
    "not mentioned", "no mention", "unspecified", "not recorded", "silent on barrier"
]


@dataclass
class EvidenceSpan:
    text: str
    span: tuple[int, int]
    category: Optional[str] = None


@dataclass
class BarrierAssessment:
    status: str                         # "confirmed" | "uncertain" | "explicitly_absent" | "not_mentioned"
    gap_severity: Optional[float]       # 0.0, 0.6, 1.0, or None for not_mentioned
    evidence: list[EvidenceSpan] = field(default_factory=list)
    confidence: float = 0.80


def _find_phrase_spans(raw_text: str, phrase: str) -> list[tuple[int, int]]:
    """Case-insensitive substring search returning character offsets in raw_text."""
    raw_lower = raw_text.lower()
    phrase_lower = phrase.lower()
    spans = []
    start = 0
    while True:
        idx = raw_lower.find(phrase_lower, start)
        if idx == -1:
            break
        spans.append((idx, idx + len(phrase)))
        start = idx + 1
    return spans


def extract_location(raw_text: str) -> dict:
    """Extract location using prototype/synthetic site vocabulary."""
    for site in PROTOTYPE_SITES:
        idx = raw_text.find(site)
        if idx != -1:
            span = (idx, idx + len(site))
            return {
                "value": site,
                "span": span,
                "confidence": 0.95,
                "evidence": EvidenceSpan(text=raw_text[span[0]:span[1]], span=span, category="location")
            }
    return {"value": None, "span": None, "confidence": 0.0, "evidence": None}


def extract_category_matches(raw_text: str, keyword_groups: dict[str, list[str]]) -> dict:
    """Find all matching phrases and character spans for category keyword groups."""
    matches_by_cat: dict[str, list[EvidenceSpan]] = {}
    for cat, phrases in keyword_groups.items():
        cat_ev = []
        for phrase in phrases:
            for span in _find_phrase_spans(raw_text, phrase):
                cat_ev.append(EvidenceSpan(text=raw_text[span[0]:span[1]], span=span, category=cat))
        if cat_ev:
            matches_by_cat[cat] = cat_ev

    best_cat = None
    if matches_by_cat:
        # Most matches first, earliest span as tie breaker
        best_cat = max(
            matches_by_cat,
            key=lambda c: (len(matches_by_cat[c]), -min(e.span[0] for e in matches_by_cat[c]))
        )

    return {"best_category": best_cat, "matches": matches_by_cat}


def extract_activity(raw_text: str, ontology_activities: Optional[list[str]] = None) -> dict:
    """Extract activity with raw text span and confidence."""
    # Check ontology activities first
    if ontology_activities:
        for act in ontology_activities:
            spans = _find_phrase_spans(raw_text, act)
            if spans:
                s = spans[0]
                return {
                    "text": raw_text[s[0]:s[1]],
                    "span": s,
                    "confidence": 0.90,
                    "category": act,
                }

    # Match keyword groups
    res = extract_category_matches(raw_text, ACTIVITY_KEYWORD_GROUPS)
    best_cat = res["best_category"]
    if best_cat and res["matches"][best_cat]:
        first_match = res["matches"][best_cat][0]
        return {
            "text": first_match.text,
            "span": first_match.span,
            "confidence": 0.85,
            "category": best_cat,
        }

    return {
        "text": "general industrial activity",
        "span": (0, min(len(raw_text), 30)),
        "confidence": 0.50,
        "category": "unspecified",
    }


# ---------------------------------------------------------------------------
# Barrier Domain Concepts
# ---------------------------------------------------------------------------
BARRIER_TERMS = [
    "isolation", "permit", "ptw", "exclusion zone", "gas test", "gas testing",
    "gas monitoring", "loto", "lockout", "tagout", "harness", "barricade",
    "guard", "scaffold tag", "barrier", "sign-off", "lock-out", "tag-out"
]


def extract_exposure(raw_text: str) -> dict:
    """Negation-aware exposure extraction. Explicit absence checked first."""
    # 1. Check explicit no-exposure phrases FIRST
    no_exp_evidence = []
    for phrase in NO_EXPOSURE_PHRASES:
        for span in _find_phrase_spans(raw_text, phrase):
            no_exp_evidence.append(EvidenceSpan(text=raw_text[span[0]:span[1]], span=span, category="no_exposure"))

    # 2. Check proximity phrases
    raw_proximity_res = extract_category_matches(raw_text, EXPOSURE_KEYWORD_GROUPS)

    # Filter out proximity matches that are simply substrings within no-exposure phrases
    # (e.g. "in the vicinity" inside "no personnel were in the vicinity")
    filtered_prox_matches: dict[str, list[EvidenceSpan]] = {}
    for cat, ev_list in raw_proximity_res["matches"].items():
        valid_ev = []
        for ev in ev_list:
            is_subspan = any(
                ev.span[0] >= no_ev.span[0] and ev.span[1] <= no_ev.span[1]
                for no_ev in no_exp_evidence
            )
            if not is_subspan:
                valid_ev.append(ev)
        if valid_ev:
            filtered_prox_matches[cat] = valid_ev

    best_prox = None
    if filtered_prox_matches:
        best_prox = max(
            filtered_prox_matches,
            key=lambda c: (len(filtered_prox_matches[c]), -min(e.span[0] for e in filtered_prox_matches[c]))
        )

    has_no_exp = len(no_exp_evidence) > 0
    has_direct = best_prox == "direct_proximity"
    has_indirect = best_prox == "indirect_proximity"

    # Flag contradiction only if an external proximity claim clashes with no-exposure
    contradiction_detected = bool(has_no_exp and (has_direct or has_indirect))

    if has_no_exp and not has_direct:
        first_ev = no_exp_evidence[0]
        return {
            "label": "no_exposure",
            "span": first_ev.span,
            "text": first_ev.text,
            "confidence": 0.92,
            "evidence": no_exp_evidence,
            "contradiction_detected": contradiction_detected,
        }

    if best_prox and filtered_prox_matches[best_prox]:
        first_ev = filtered_prox_matches[best_prox][0]
        return {
            "label": best_prox,
            "span": first_ev.span,
            "text": first_ev.text,
            "confidence": 0.88 if not contradiction_detected else 0.50,
            "evidence": filtered_prox_matches[best_prox],
            "contradiction_detected": contradiction_detected,
            "competing_no_exposure_evidence": no_exp_evidence if contradiction_detected else [],
        }

    if has_no_exp:
        first_ev = no_exp_evidence[0]
        return {
            "label": "no_exposure",
            "span": first_ev.span,
            "text": first_ev.text,
            "confidence": 0.85,
            "evidence": no_exp_evidence,
            "contradiction_detected": False,
        }

    return {
        "label": "unspecified",
        "span": None,
        "text": "",
        "confidence": 0.40,
        "evidence": [],
        "contradiction_detected": False,
    }


def extract_barrier_status(raw_text: str, window_words: int = 4) -> BarrierAssessment:
    """Extract barrier status using 4 distinct states.
    
    States:
    - confirmed:         gap_severity = 0.0
    - uncertain:         gap_severity = 0.6
    - explicitly_absent: gap_severity = 1.0
    - not_mentioned:     gap_severity = None (review required / insufficient info)
    """
    raw_lower = raw_text.lower()
    words = re.findall(r"[a-zA-Z0-9']+", raw_lower)

    # 1. Explicit absence phrases (e.g. "no isolation was mentioned", "without a permit")
    absence_evidence = []
    for phrase in EXPLICIT_ABSENCE_PHRASES:
        for span in _find_phrase_spans(raw_text, phrase):
            absence_evidence.append(EvidenceSpan(text=raw_text[span[0]:span[1]], span=span, category="explicitly_absent"))

    if absence_evidence:
        return BarrierAssessment(
            status="explicitly_absent",
            gap_severity=1.0,
            evidence=absence_evidence,
            confidence=0.92,
        )

    # If no barrier concept is present in the text at all, it is definitely not_mentioned
    has_any_barrier_term = any(
        re.search(r"\b" + re.escape(term) + r"\b", raw_lower)
        for term in BARRIER_TERMS
    )
    if not has_any_barrier_term:
        return BarrierAssessment(
            status="not_mentioned",
            gap_severity=None,
            evidence=[],
            confidence=0.85,
        )

    # 2. Check for confirmation targets and local negation
    affirmed_evidence = []
    negated_evidence = []
    for term in CONFIRMATION_TARGETS:
        for m in re.finditer(r"\b" + re.escape(term) + r"\b", raw_lower):
            prefix_tokens = re.findall(r"[a-zA-Z0-9']+", raw_lower[:m.start()])
            tok_idx = len(prefix_tokens)
            window_toks = words[max(0, tok_idx - window_words):tok_idx]
            window_bigrams = [" ".join(window_toks[j:j + 2]) for j in range(len(window_toks) - 1)]

            is_neg = (
                any(c in window_toks for c in NEGATION_CUES_SINGLE) or
                any(c in window_bigrams for c in NEGATION_CUES_MULTI)
            )
            ev = EvidenceSpan(text=raw_text[m.start():m.end()], span=(m.start(), m.end()), category="confirmation")
            if is_neg:
                negated_evidence.append(ev)
            else:
                affirmed_evidence.append(ev)

    if negated_evidence and not affirmed_evidence:
        # Negated confirmation (e.g., "isolation was not clearly confirmed") -> genuine uncertainty
        return BarrierAssessment(
            status="uncertain",
            gap_severity=0.6,
            evidence=negated_evidence,
            confidence=0.82,
        )
    if negated_evidence and affirmed_evidence:
        # Mixed barrier signals in the report
        return BarrierAssessment(
            status="uncertain",
            gap_severity=0.6,
            evidence=negated_evidence + affirmed_evidence,
            confidence=0.75,
        )
    if affirmed_evidence:
        return BarrierAssessment(
            status="confirmed",
            gap_severity=0.0,
            evidence=affirmed_evidence,
            confidence=0.90,
        )

    # 3. Check explicit "not mentioned" cues
    explicit_no_mention = []
    for phrase in NO_MENTION_PHRASES:
        for span in _find_phrase_spans(raw_text, phrase):
            explicit_no_mention.append(EvidenceSpan(text=raw_text[span[0]:span[1]], span=span, category="not_mentioned"))

    # Barrier details omitted entirely -> not_mentioned with gap_severity = None
    return BarrierAssessment(
        status="not_mentioned",
        gap_severity=None,
        evidence=explicit_no_mention,
        confidence=0.70,
    )


def extract_evidence(raw_text: str, ontology_activities: Optional[list[str]] = None) -> dict:
    """Stage 1 primary evidence extraction interface.
    
    All character spans are exact slices of raw_text.
    """
    activity = extract_activity(raw_text, ontology_activities=ontology_activities)
    hazard = extract_category_matches(raw_text, HAZARD_KEYWORD_GROUPS)
    exposure = extract_exposure(raw_text)
    barrier = extract_barrier_status(raw_text)
    location = extract_location(raw_text)

    return {
        "activity": activity,
        "hazard": hazard,
        "exposure": exposure,
        "barrier": barrier,
        "location": location,
        "raw_text": raw_text,
    }
