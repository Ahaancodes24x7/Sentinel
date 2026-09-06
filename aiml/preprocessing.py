"""
PS 26165 — Stage 0: Preprocessing (Legacy Module Wrapper)
==========================================================
Re-exports from sif_engine.preprocessing for backward compatibility.
Primary import location: sif_engine.preprocessing
"""

from sif_engine.preprocessing import (
    ABBREVIATIONS,
    CODE_MIXED_GLOSSARY,
    TYPO_CORRECTIONS,
    FUZZY_VOCAB,
    PROTECTED_WORDS,
    expand_abbreviations,
    translate_code_mixed,
    correct_typos,
    normalize_whitespace_punct,
    preprocess_report,
    preprocess_report_with_metadata,
)

__all__ = [
    "ABBREVIATIONS",
    "CODE_MIXED_GLOSSARY",
    "TYPO_CORRECTIONS",
    "FUZZY_VOCAB",
    "PROTECTED_WORDS",
    "expand_abbreviations",
    "translate_code_mixed",
    "correct_typos",
    "normalize_whitespace_punct",
    "preprocess_report",
    "preprocess_report_with_metadata",
]


if __name__ == "__main__":
    samples = [
        "No PTW was sighted. LOTO tag #482 not confimed. Mazdoor ko turant hataya gaya.",
        "Wielding activity near PMCC without isolaton; supervsor ne bola area khali tha (PTW ref attached).",
        "H2S detected near confined space entry, SCBA not verifed before entry - safty breach.",
    ]
    for s in samples:
        print("RAW :", s)
        print("CLEAN:", preprocess_report(s))
        print()
