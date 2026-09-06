"""Stage 0 preprocessing pipeline for safety reports."""

import re

from .abbreviations import expand_abbreviations
from .code_mixed import translate_code_mixed
from .typo_correction import correct_typos


def normalize_whitespace_punct(text: str) -> str:
    """Remove known report noise and normalize whitespace and punctuation.
    Content-removing substitutions must run BEFORE whitespace collapsing,
    otherwise removing a token (e.g. "#482") leaves a double space behind.
    """
    text = re.sub(r"\(.*?ref.*?\)", "", text, flags=re.IGNORECASE)   # strip "(PTW ref attached)"-style noise
    text = re.sub(r"#\d+", "", text)                                  # strip tag numbers like "LOTO tag #482"
    text = re.sub(r"\s+([.,])", r"\1", text)                          # no space before punctuation
    text = re.sub(r"\s+", " ", text)                                  # collapse whitespace LAST
    return text.strip()


def preprocess_report(text: str, lowercase: bool = True) -> str:
    """Full Stage 0 pipeline, in the required order."""
    text = expand_abbreviations(text)          # step 1 — case-sensitive, before lowercasing
    text = translate_code_mixed(text)          # step 2
    if lowercase:
        text = text.lower()                    # step 3
    text = correct_typos(text)                 # step 4
    text = normalize_whitespace_punct(text)    # step 5
    return text


def preprocess_report_with_metadata(text: str, lowercase: bool = True) -> dict:
    """Run full Stage 0 preprocessing and return preprocessed text along with metadata."""
    original_text = text
    abbr_text = expand_abbreviations(original_text)
    translated_text = translate_code_mixed(abbr_text)
    lowered_text = translated_text.lower() if lowercase else translated_text
    corrected_text = correct_typos(lowered_text)
    final_text = normalize_whitespace_punct(corrected_text)

    return {
        "raw_text": original_text,
        "abbreviations_expanded": abbr_text != original_text,
        "code_mixed_translated": translated_text != abbr_text,
        "typos_corrected": corrected_text != lowered_text,
        "preprocessed_text": final_text,
    }