"""Contextual Safety Environment Extractor for OIL Operations.

Extracts operational safety environment context directly from raw report text:
- 17 distinct industrial/field categories
- Preserves exact raw character spans: raw_text[start:end] == span_text
- Negation-aware: detects negated environmental context (e.g. "not in a confined space")
- Transparent provenance tracking ('exact_span' | 'none')
- CRITICAL: Environment context is strictly descriptive and does NOT manufacture
  SIF precursors in the absence of high-energy hazards and barrier gaps.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class EnvironmentSpan:
    category: str
    text: str
    span: tuple[int, int]
    confidence: float
    negated: bool = False
    provenance: str = "exact_span"


# ---------------------------------------------------------------------------
# 17 Industrial Categories with Domain Patterns
# ---------------------------------------------------------------------------
ENVIRONMENT_PATTERNS: dict[str, list[str]] = {
    "night_work": [
        "night shift", "night work", "after dark", "working at night"
    ],
    "weather_exposure": [
        "heavy rain", "rain", "severe weather", "storm conditions", "wet weather"
    ],
    "offshore_drilling": [
        "offshore rig", "drilling platform", "jackup rig", "offshore barge",
        "drillship", "offshore installation"
    ],
    "onshore_drilling": [
        "drilling rig", "mast", "derrick", "drilling floor", "drill floor",
        "substructure", "kelly bushing", "mud pump", "drawworks", "rig floor"
    ],
    "pipeline_operations": [
        "pipeline corridor", "right of way", "pipeline right-of-way", "row",
        "pig launcher", "pig receiver", "trunkline", "flowline", "pipeline trench",
        "feeder line", "pipeline"
    ],
    "refinery_process": [
        "refinery unit", "distillation column", "hydrocracker", "process plant",
        "fractionator", "furnace unit", "battery limit", "process manifold"
    ],
    "confined_space": [
        "confined space", "storage tank", "sludge pit", "vessel interior",
        "enclosed sump", "separator tank", "crude storage tank", "degasser vessel",
        "boiler drum", "inside vessel", "inside tank"
    ],
    "elevated_work": [
        "scaffolding", "pipe rack", "monkey board", "derrick board",
        "elevated platform", "aerial basket", "ladder access", "mast ladder",
        "flare stack", "roof structure", "high structure", "at height"
    ],
    "electrical_substation": [
        "electrical substation", "substation", "transformer bay", "switchgear room",
        "motor control center", "mcc room", "high voltage yard", "battery bank room",
        "generator room", "switchyard"
    ],
    "chemical_handling": [
        "chemical injection skid", "dosing unit", "acid storage", "demulsifier tank",
        "biocide handling", "corrosion inhibitor store", "chemical preparation area",
        "chemical warehouse"
    ],
    "hot_work_area": [
        "welding booth", "fabrication yard", "hot work zone", "pipe fabrication shop",
        "open flame permit area", "cutting shop"
    ],
    "vehicle_traffic": [
        "heavy vehicle yard", "crude dispatch terminal", "access road", "loading bay",
        "haulage route", "parking yard", "internal plant road", "tanker loading bay"
    ],
    "crane_lifting_zone": [
        "crane lifting radius", "crane pad", "lifting zone", "rigging bay",
        "heavy lift corridor", "boom operating radius", "overhead crane bay"
    ],
    "excavation_trench": [
        "excavation pit", "trenching site", "buried pipe trench", "earthworks zone",
        "shored trench", "foundation pit", "open ditch"
    ],
    "high_pressure_manifold": [
        "well testing manifold", "production manifold", "choke manifold",
        "high pressure flow manifold", "injection manifold", "kill manifold",
        "standpipe manifold"
    ],
    "marine_loading": [
        "river terminal jetty", "barge berth", "jetty loading arm", "marine dock",
        "river crossing terminal", "waterway depot"
    ],
    "wellhead_operations": [
        "christmas tree", "xmas tree", "wellhead cellar", "producing wellhead",
        "annulus line", "casing head", "wellhead", "tubing spool"
    ],
    "gas_compression": [
        "compressor station", "gas compressor house", "gas booster unit",
        "compressor manifold", "refrigeration compressor unit"
    ],
    "workshop_maintenance": [
        "mechanical workshop", "maintenance shed", "machine tool room",
        "valve servicing shop", "instrumentation workshop", "central workshop"
    ],
}

# ---------------------------------------------------------------------------
# Negation Cues for Environmental Context
# ---------------------------------------------------------------------------
ENV_NEGATION_PREFIXES = [
    "not in", "outside of", "outside the", "no entry into", "not within",
    "away from", "not at", "without entering", "exterior to", "not an"
]


def _is_negated(raw_text: str, match_start: int, window_chars: int = 40) -> bool:
    """Check if the text immediately preceding the match contains an environmental negation."""
    prefix_start = max(0, match_start - window_chars)
    prefix_text = raw_text[prefix_start:match_start].lower()
    return any(neg in prefix_text for neg in ENV_NEGATION_PREFIXES)


def extract_environment(raw_text: str) -> dict[str, Any]:
    """Extract contextual safety environment with exact raw spans and negation awareness.
    
    Returns:
        dict with:
            - category: Primary detected environment category (or None)
            - text: Matched text slice in raw text
            - span: tuple[int, int] | None
            - confidence: float
            - negated: bool
            - provenance: "exact_span" | "none"
            - all_detected: list[dict]
    """
    raw_lower = raw_text.lower()
    detected_spans: list[EnvironmentSpan] = []

    for cat, phrases in ENVIRONMENT_PATTERNS.items():
        for phrase in phrases:
            start = 0
            while True:
                idx = raw_lower.find(phrase, start)
                if idx == -1:
                    break
                end = idx + len(phrase)
                exact_text = raw_text[idx:end]
                negated = _is_negated(raw_text, idx)
                detected_spans.append(
                    EnvironmentSpan(
                        category=cat,
                        text=exact_text,
                        span=(idx, end),
                        confidence=0.88 if not negated else 0.40,
                        negated=negated,
                        provenance="exact_span",
                    )
                )
                start = idx + 1

    # Filter out affirmative detections vs negated detections
    affirmative = [s for s in detected_spans if not s.negated]

    all_detected_dicts = [
        {
            "category": s.category,
            "text": s.text,
            "span": s.span,
            "confidence": s.confidence,
            "negated": s.negated,
            "provenance": s.provenance,
        }
        for s in detected_spans
    ]

    if affirmative:
        # Choose primary affirmative environment (earliest span occurrence)
        best = min(affirmative, key=lambda s: s.span[0])
        return {
            "category": best.category,
            "text": best.text,
            "span": best.span,
            "confidence": best.confidence,
            "negated": False,
            "provenance": "exact_span",
            "all_detected": all_detected_dicts,
        }

    if detected_spans:
        # Only negated matches exist
        first_neg = detected_spans[0]
        return {
            "category": first_neg.category,
            "text": first_neg.text,
            "span": first_neg.span,
            "confidence": first_neg.confidence,
            "negated": True,
            "provenance": "exact_span",
            "all_detected": all_detected_dicts,
        }

    return {
        "category": None,
        "text": None,
        "span": None,
        "confidence": 0.0,
        "negated": False,
        "provenance": "none",
        "all_detected": [],
    }
