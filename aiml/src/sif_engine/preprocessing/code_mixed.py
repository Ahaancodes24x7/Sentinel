"""Literal safety-vocabulary normalization for code-mixed field reports."""

import re

CODE_MIXED_GLOSSARY = {
    "mazdoor":            "worker",
    "mazdoor ko":         "the worker",
    "kaam":               "work",
    "kaam kar raha tha":  "was working",
    "khatra":             "hazard",
    "khatarnak":          "dangerous",
    "turant":             "immediately",
    "dekha":              "noticed",
    "dekha gaya":         "was observed",
    "bina":               "without",
    "bina isolation ke":  "without isolation",
    "jaldi":              "quickly",
    "sahi":               "correct",
    "galat":              "incorrect",
    "supervisor ne bola": "supervisor instructed",
    "check nahi kiya":    "was not checked",
    "permit nahi tha":    "no permit was in place",
    "area khali tha":     "area was clear",
    "area khali nahi tha": "area was not clear",
    "hataya gaya":         "was removed",
    "hataya":              "removed",
}


def translate_code_mixed(text: str) -> str:
    """Replace longest code-mixed phrases before shorter overlapping terms."""
    for phrase, translation in sorted(CODE_MIXED_GLOSSARY.items(), key=lambda x: -len(x[0])):
        pattern = r"\b" + re.escape(phrase) + r"\b"
        text = re.sub(pattern, translation, text, flags=re.IGNORECASE)
    return text