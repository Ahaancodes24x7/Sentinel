"""Keyword/rule baseline for SIF-potential classification (Baseline B1).

Intentionally simple. Its job is to answer "how much of this task is solvable
by surface-form matching?" and to double as the first set of weak-supervision
labelling functions. It should NOT score well — if a keyword bag matched the
hybrid reasoner, the reasoning layer would not be earning its place.

The decision mirrors the SCL structure: high-energy cue present, AND some
signal that a control is missing or unverified, AND some signal that a person
was exposed. Requiring all three is what stops it flagging every report that
merely mentions a crane.
"""

from typing import Optional

HIGH_ENERGY_KEYWORDS = [
    "hot work", "welding", "grinding", "cutting torch", "spark", "flame",
    "suspended load", "crane", "hoist", "sling", "rigging", "lifting", "boom",
    "confined space", "tank entry", "vessel entry", "h2s", "oxygen deficient",
    "gas test", "purge", "electrical", "energised", "energized", "live",
    "switchgear", "transformer", "busbar", "pmcc", "breaker", "11kv", "440v",
    "isolation", "loto", "lockout", "pressure", "pressurised", "pressurized",
    "hydraulic", "pneumatic", "blowdown", "wellhead", "line of fire",
    "dropped object", "falling object", "tension", "whip", "pig launcher",
    "rotating", "coupling", "drawworks", "top drive", "guard",
    "height", "scaffold", "harness", "fall arrest", "derrick", "monkey board",
    "vehicle", "reversing", "forklift", "tanker", "banksman",
    "bypass", "override", "inhibit", "interlock", "esd", "trip",
    "radiography", "radioactive", "norm", "gamma", "iridium",
    "flammable", "hydrocarbon", "lel", "gas leak", "condensate",
    "chemical", "caustic", "acid", "methanol", "corrosive",
]

BARRIER_GAP_KEYWORDS = [
    "not clearly confirmed", "could not be located", "not mentioned",
    "no isolation", "no exclusion zone", "without a permit", "without the",
    "not re-verified", "not actively enforced", "not confirmed",
    "could not be confirmed", "not verified", "not evidenced",
    "had not been established", "was not in place", "no evidence of",
    "was bypassed", "was removed", "unclear", "nobody could confirm",
    "not re-verified", "scope had since changed", "work proceeded without",
    "no permit", "not sighted", "missing", "expired", "unverified",
    "was inhibited", "was overridden", "was disabled", "was jumpered",
]

EXPOSURE_KEYWORDS = [
    "within", "beneath", "underneath", "inside", "directly", "arm's reach",
    "nearby", "in the line of fire", "at the point of exposure",
    "hands inside", "in front of", "downwind", "splash zone", "open edge",
    "blind spot", "immediate work zone", "in contact with", "head inside",
    "discharge side", "swing radius", "in the path of", "standing",
    "positioned", "was working", "personnel were", "a worker was",
]


def _hits(text: str, keywords: list[str]) -> list[str]:
    return [k for k in keywords if k in text]


def rule_predict(text: str) -> int:
    """Return the keyword-rule SIF-potential prediction (0/1)."""
    return int(bool(rule_explain(text)["prediction"]))


def rule_explain(text: str) -> dict:
    """Same decision, with the matched cues — these double as weak-supervision
    labelling functions, so the evidence has to come back out."""
    lowered = (text or "").lower()
    energy = _hits(lowered, HIGH_ENERGY_KEYWORDS)
    gap = _hits(lowered, BARRIER_GAP_KEYWORDS)
    exposure = _hits(lowered, EXPOSURE_KEYWORDS)
    prediction = int(bool(energy) and bool(gap) and bool(exposure))
    return {
        "prediction": prediction,
        "energy_cues": energy[:6],
        "barrier_gap_cues": gap[:6],
        "exposure_cues": exposure[:6],
    }


__all__ = [
    "rule_predict",
    "rule_explain",
    "HIGH_ENERGY_KEYWORDS",
    "BARRIER_GAP_KEYWORDS",
    "EXPOSURE_KEYWORDS",
]
