"""Abbreviation and oil-and-gas jargon expansion for Stage 0 preprocessing."""

import re

ABBREVIATIONS = {
    "LOTO":   "lockout tagout isolation",
    "PTW":    "permit to work",
    "HSSE":   "health safety security environment",
    "UA/UC":  "unsafe act unsafe condition",
    "UA":     "unsafe act",
    "UC":     "unsafe condition",
    "SIMOPS": "simultaneous operations",
    "PMCC":   "power motor control center",
    "PPE":    "personal protective equipment",
    "JSA":    "job safety analysis",
    "HAZOP":  "hazard and operability study",
    "HAZID":  "hazard identification",
    "MSDS":   "material safety data sheet",
    "SCBA":   "self contained breathing apparatus",
    "PSV":    "pressure safety valve",
    "ESD":    "emergency shutdown",
    "MOC":    "management of change",
    "SOP":    "standard operating procedure",
    "TBT":    "toolbox talk",
    "NCR":    "non conformance report",
    "CAPA":   "corrective and preventive action",
    "OIM":    "offshore installation manager",
    "RA":     "risk assessment",
    "H2S":    "hydrogen sulphide gas",
    "LEL":    "lower explosive limit",
    "EX":     "explosion proof",
    "EWP":    "elevated work platform",
    "MEWP":   "mobile elevated work platform",
    "IOGP":   "international association of oil and gas producers",
    "LSR":    "life saving rule",
    "SWA":    "stop work authority",
    "PM":     "preventive maintenance",
    "OIL":    "oil india limited",
}


def expand_abbreviations(text: str) -> str:
    """Case-sensitive whole-word replacement, run BEFORE lowercasing."""
    for abbr, full in sorted(ABBREVIATIONS.items(), key=lambda x: -len(x[0])):
        pattern = r"\b" + re.escape(abbr) + r"\b"
        text = re.sub(pattern, full, text)
    return text