"""Domain-specific typo correction with protected expansion words."""

import difflib

from .abbreviations import ABBREVIATIONS
from .code_mixed import CODE_MIXED_GLOSSARY

TYPO_CORRECTIONS = {
    "isolaton":      "isolation",
    "isolaion":      "isolation",
    "electical":     "electrical",
    "electricl":     "electrical",
    "maintainance":  "maintenance",
    "maintenence":   "maintenance",
    "safty":         "safety",
    "saftey":        "safety",
    "hazerdous":     "hazardous",
    "hazardus":      "hazardous",
    "confimed":      "confirmed",
    "confrimed":     "confirmed",
    "excavtion":     "excavation",
    "excavaton":     "excavation",
    "supervsor":     "supervisor",
    "supervizor":    "supervisor",
    "permitt":       "permit",
    "wielding":      "welding",
    "weldng":        "welding",
    "verfied":       "verified",
    "verifed":       "verified",
    "exlusion":      "exclusion",
    "exclustion":    "exclusion",
    "sispended":     "suspended",
    "suspeded":      "suspended",
}

FUZZY_VOCAB = list(set(
    list(TYPO_CORRECTIONS.values()) + [
        "isolation", "electrical", "maintenance", "safety", "hazardous",
        "confirmed", "excavation", "supervisor", "permit", "welding",
        "verified", "exclusion", "suspended", "energized", "confined",
        "lifting", "crane", "scaffolding", "pipeline", "inspection",
    ]
))

PROTECTED_WORDS = set()
for _phrase in list(ABBREVIATIONS.values()) + list(CODE_MIXED_GLOSSARY.values()):
    PROTECTED_WORDS.update(_phrase.lower().split())


def correct_typos(text: str, fuzzy: bool = True, fuzzy_cutoff: float = 0.82) -> str:
    """Correct known typos and optionally use controlled fuzzy vocabulary."""
    tokens = text.split()
    corrected = []
    for tok in tokens:
        stripped = tok.strip(".,;:()").lower()
        if stripped in PROTECTED_WORDS:
            corrected.append(tok)
            continue
        if stripped in TYPO_CORRECTIONS:
            corrected.append(TYPO_CORRECTIONS[stripped])
            continue
        # Hyphenated compounds (re-verified, co-worker, non-conformance) are
        # legitimate words, not typos. Fuzzy string similarity treats them as
        # near-matches to their root word (e.g. "re-verified" ~ "verified",
        # ratio 0.84) and would silently strip a meaning-bearing prefix like
        # "re-" or "non-". Never fuzzy-correct a token containing a hyphen.
        if fuzzy and len(stripped) > 4 and "-" not in stripped:
            match = difflib.get_close_matches(stripped, FUZZY_VOCAB, n=1, cutoff=fuzzy_cutoff)
            if match and match[0] != stripped:
                corrected.append(match[0])
                continue
        corrected.append(tok)
    return " ".join(corrected)