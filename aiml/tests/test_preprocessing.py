"""
PS 26165 — Stage 0 preprocessing test suite.
Run with: pytest or python -m pytest or python tests/test_preprocessing.py
"""

from sif_engine.preprocessing import (
    expand_abbreviations,
    translate_code_mixed,
    correct_typos,
    normalize_whitespace_punct,
    preprocess_report,
    preprocess_report_with_metadata,
)


def test_abbreviation_expansion_ptw_loto():
    """Verify PTW and LOTO abbreviations expand correctly."""
    result = expand_abbreviations("No PTW sighted. LOTO tag not confirmed.")
    assert "permit to work" in result
    assert "lockout tagout isolation" in result


def test_abbreviation_expansion_no_substring_corruption():
    """Verify abbreviation matching does not corrupt substrings inside words (e.g. OIL in boiler)."""
    result = expand_abbreviations("The boiler was inspected.")
    assert "boiler was inspected" in result


def test_code_mixed_translation_idiom_priority():
    """Verify multi-word code-mixed idioms are preferred over single-word overlaps."""
    result = translate_code_mixed("bina isolation ke kaam shuru hua")
    assert "without isolation" in result


def test_code_mixed_translation_hataya_gaya():
    """Verify Hindi phrase translation for hataya gaya."""
    result = translate_code_mixed("mazdoor ko turant hataya gaya")
    assert "was removed" in result


def test_typo_correction_known_dictionary():
    """Verify known typo dictionary corrections."""
    result = correct_typos("isolaton was not confimed")
    assert "isolation" in result
    assert "confirmed" in result


def test_failure_case_scba_not_confined():
    """Failure case 1: 'self contained breathing apparatus' must NOT become 'self confined breathing apparatus'."""
    raw = "self contained breathing apparatus"
    result = correct_typos(raw)
    assert "contained" in result
    assert "self confined breathing" not in result

    full_result = preprocess_report("H2S detected, SCBA not verifed before entry - safty breach.")
    assert "self contained breathing apparatus" in full_result
    assert "self confined" not in full_result


def test_failure_case_tag_number_no_double_space():
    """Failure case 2: stripping '#482' must not leave double spaces."""
    result = normalize_whitespace_punct("isolation tag #482 not confirmed")
    assert "isolation tag not confirmed" in result
    assert "  " not in result


def test_failure_case_re_verified_fuzzy_protection():
    """Failure case 3: 're-verified' must not be changed by fuzzy correction."""
    raw = "gas test done earlier, not re-verified before entry"
    result = correct_typos(raw)
    assert "re-verified" in result
    assert "not verified before" not in result


def test_failure_case_not_re_verified_meaning():
    """Failure case 4: 'not re-verified' must retain its meaning in full preprocessing pipeline."""
    raw = "gas test reportedly done earlier in shift, not re-verified before entry"
    result = preprocess_report(raw)
    assert "not re-verified" in result


def test_raw_input_remains_unchanged():
    """Failure case 5: raw input text must never be modified in-place."""
    raw_original = "No PTW sighted. LOTO tag #482 not confimed."
    raw_copy = str(raw_original)

    _ = expand_abbreviations(raw_original)
    assert raw_original == raw_copy

    _ = translate_code_mixed(raw_original)
    assert raw_original == raw_copy

    _ = correct_typos(raw_original)
    assert raw_original == raw_copy

    _ = normalize_whitespace_punct(raw_original)
    assert raw_original == raw_copy

    _ = preprocess_report(raw_original)
    assert raw_original == raw_copy

    _ = preprocess_report_with_metadata(raw_original)
    assert raw_original == raw_copy


def test_preprocess_report_end_to_end_samples():
    """Verify end-to-end preprocessing on sample field reports."""
    res1 = preprocess_report("Wielding activity near PMCC without isolaton; supervsor ne bola area khali tha (PTW ref attached).")
    assert "welding" in res1
    assert "power motor control center" in res1
    assert "isolation" in res1
    assert "supervisor instructed" in res1 or "supervisor ne bola" in res1
    assert "area was clear" in res1

    res2 = preprocess_report("H2S detected near confined space entry, SCBA not verifed before entry - safty breach.")
    assert "self contained breathing apparatus" in res2
    assert "verified" in res2
    assert "safety" in res2


def test_preprocess_report_with_metadata():
    """Verify preprocess_report_with_metadata returns structured transformation info."""
    meta = preprocess_report_with_metadata("No PTW was sighted. LOTO tag #482 not confimed.")
    assert meta["raw_text"] == "No PTW was sighted. LOTO tag #482 not confimed."
    assert meta["abbreviations_expanded"] is True
    assert meta["typos_corrected"] is True
    assert "permit to work" in meta["preprocessed_text"]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__]))
