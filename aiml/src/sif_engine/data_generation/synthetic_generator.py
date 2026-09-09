"""Synthetic UA/UC (Unsafe Act / Unsafe Condition) report generator — Sentinel v2.

IMPORTANT: This generates SYNTHETIC data only. It is NOT real OIL India data.
Every row carries source="synthetic" and the dashboard renders a permanent
"Synthetic Demonstration Dataset" banner off the back of that field.

What makes this generator different from a naive template filler:

1.  **Gold character spans.** Text is assembled from labelled segments, so the
    exact ``[start, end)`` offsets of the activity / hazard / barrier / exposure /
    location phrases are known *in the noisy text the model actually sees*.
    That is what makes supervised NER training (and span-F1 evaluation)
    possible at all.

2.  **SCL-faithful ground truth.** The label follows the EEI Safety
    Classification & Learning decision logic — high energy present, exposure
    occurred, and no *direct* control in place — and deliberately does NOT
    depend on the stated outcome. A "no injury" near-miss with an absent
    barrier is positive; a first-aid case behind a verified mechanical barrier
    is negative. This is the whole point of the problem statement.

3.  **A direct-control distinction.** A confirmed *administrative* barrier
    (a permit, a journey plan) does not clear a high-energy exposure the way a
    confirmed *engineering* barrier (isolation, gas test, guarding) does. This
    stops the corpus from being trivially separable on the phrase
    "not confirmed", which a keyword baseline would otherwise ace.

4.  **Realistic messiness.** Abbreviations, field typos, code-mixed
    Hindi/Assamese phrasing, terse fragments, missing punctuation and
    inconsistent casing are injected per-segment so Stage 0 preprocessing has
    genuine work to do.

5.  **Planted structure.** Recurring barrier-failure patterns, an emerging
    cluster with a late-window spike, and rare-but-severe singletons are
    deliberately seeded so the clustering, association-mining and CUSUM
    early-warning layers have real signal to find rather than noise to
    hallucinate over.
"""

from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

# --------------------------------------------------------------------------
# Ontology loading — single shared taxonomy file
# --------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "ontology.yaml"


def load_ontology(path: Optional[Path] = None) -> dict[str, Any]:
    with open(path or _CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


ONTOLOGY = load_ontology()

ACTIVITIES: list[str] = ONTOLOGY["activities"]
ENERGY_TYPES: dict[str, dict] = ONTOLOGY["energy_types"]
ACTIVITY_ENERGY_MAP: dict[str, list[str]] = ONTOLOGY["activity_energy_map"]
BARRIER_TYPES: dict[str, dict] = ONTOLOGY["barrier_types"]
SITES: list[dict] = ONTOLOGY["sites"]

# energy_type -> the barrier type that controls it
ENERGY_TO_BARRIER: dict[str, str] = {}
for _bname, _bdef in BARRIER_TYPES.items():
    for _et in _bdef["controls_energy"]:
        ENERGY_TO_BARRIER.setdefault(_et, _bname)


def is_high_energy(energy_type: str) -> bool:
    return bool(ENERGY_TYPES[energy_type]["is_high_energy"])


def lsr_for(energy_type: str) -> str:
    return ENERGY_TYPES[energy_type]["lsr_tag"]


def magnitude_of(energy_type: str) -> int:
    return int(ENERGY_TYPES[energy_type]["magnitude_class"])


# --------------------------------------------------------------------------
# Phrase banks
# --------------------------------------------------------------------------

# Barrier noun phrases, per barrier type. Multiple surface forms per barrier so
# the same underlying control shows up worded a dozen different ways — this is
# exactly the vocabulary sparsity the blueprint (Section 3.3) warns about.
BARRIER_NOUNS: dict[str, list[str]] = {
    "Energy isolation & LOTO": [
        "isolation", "the lockout-tagout", "energy isolation",
        "the isolation certificate", "the LOTO tags", "electrical isolation",
    ],
    "Permit to work": [
        "the permit to work", "the work permit", "work authorisation",
        "the permit", "the job safety analysis",
    ],
    "Gas testing & atmospheric monitoring": [
        "the gas test", "atmospheric monitoring", "the gas test certificate",
        "continuous gas monitoring", "the pre-entry gas check",
    ],
    "Exclusion zone & barricading": [
        "the exclusion zone", "barricading", "the barricade",
        "the restricted area cordon", "the drop-zone barrier",
    ],
    "Fall protection": [
        "fall arrest", "the harness anchor point", "edge protection",
        "the scaffold tag", "the fall protection system",
    ],
    "Machine guarding": [
        "the machine guard", "the coupling guard", "the guard",
        "the rotating equipment guard",
    ],
    "Traffic & journey management": [
        "the banksman", "the journey management plan", "traffic control",
        "the reversing spotter",
    ],
    "Safety instrumented system": [
        "the interlock", "the ESD trip", "the fire and gas detection",
        "the high-level alarm", "the trip system",
    ],
    "Lifting plan & rigging control": [
        "the lift plan", "the rigging inspection", "the load chart check",
        "the lifting permit",
    ],
}

# Status templates. {b} is substituted with a barrier noun phrase.
#
# These banks are deliberately large. With only a handful of templates per
# status, a bag-of-words classifier memorises the exact strings and scores ~100%
# on barrier status — which tells you nothing except that the generator is
# predictable. Expanding the surface forms (and sharing vocabulary ACROSS
# statuses, e.g. "verified" appears in both confirmed and negated-uncertain
# phrasings) forces a model to read the construction rather than spot a
# fingerprint. It does not eliminate the circularity — nothing can, on
# synthetic data — but it stops the metrics being pure theatre.
BARRIER_TEMPLATES: dict[str, list[str]] = {
    "confirmed_present": [
        "{b} was verified and signed off before work began",
        "{b} was in place and independently checked by the supervisor",
        "{b} had been completed and witnessed prior to the task",
        "{b} was confirmed effective at the start of the shift",
        "{b} was validated by the area authority and recorded",
        "{b} was physically verified at the worksite",
        "{b} was checked by two people and logged",
        "the crew confirmed {b} was applied and tested",
        "{b} was walked down with the permit holder before start-up",
        "records showed {b} was in force for the duration of the job",
        "{b} was demonstrated to the observer on request",
        "{b} had been re-tested after the last break in work",
        "the area authority satisfied himself that {b} was effective",
        "{b} was tagged, logged and cross-checked against the register",
    ],
    "uncertain": [
        "{b} status could not be confirmed by the crew",
        "{b} was reportedly completed earlier in the shift but not re-verified",
        "{b} was raised but the sign-off could not be located",
        "{b} appeared to be in place, though nobody could confirm who checked it",
        "the validity of {b} was unclear at the time of the observation",
        "{b} was mentioned in the toolbox talk but not evidenced on site",
        "{b} had been signed but the scope had since changed",
        "the crew believed {b} was applied but could not demonstrate it",
        "{b} was recorded in the log, though the entry was not timed",
        "it was unclear whether {b} still covered the work being done",
        "{b} was said to have been verified, but by whom was not established",
        "the observer could not establish the current status of {b}",
        "{b} was in place earlier, but its condition at the time is unknown",
        "no one on site could confirm when {b} was last checked",
    ],
    "explicitly_absent": [
        "no {b} was in place at the time",
        "{b} had not been established when work started",
        "work proceeded without {b}",
        "{b} was found to have been removed before the task was complete",
        "there was no evidence of {b} anywhere at the worksite",
        "{b} was bypassed to save time during the shift",
        "{b} was absent and the job continued regardless",
        "the crew started work before {b} was arranged",
        "{b} had been dismantled and not reinstated",
        "there was no {b} covering the activity being carried out",
        "{b} was deliberately set aside to meet the schedule",
        "the observer confirmed {b} was not applied at all",
    ],
    "not_mentioned": [""],
}

# Hazard / energy surface phrases — what the reporter actually writes.
HAZARD_PHRASES: dict[str, list[str]] = {
    "stored/electrical energy": [
        "the 440V panel was still energised", "live busbars were exposed",
        "the switchgear remained energized", "stored energy in the capacitor bank",
        "the PMCC feeder was live", "an 11kV cable was not proven dead",
    ],
    "pressure/hydraulic energy": [
        "the line was still under pressure", "trapped pressure in the flowline",
        "the hydraulic accumulator had not been bled off",
        "the header was pressurised to 40 bar", "residual wellhead pressure remained",
    ],
    "thermal (hot work)": [
        "welding was underway", "a cutting torch was in use",
        "grinding sparks were falling into the drain", "hot work was in progress",
        "the burner was lit adjacent to the line",
    ],
    "flammable/explosive atmosphere": [
        "a hydrocarbon smell was reported", "a gas leak was detected nearby",
        "LEL readings were rising at the work front",
        "condensate had spilled close to an ignition source",
        "flammable vapour was drifting across the area",
    ],
    "gravitational (suspended load)": [
        "a suspended load was overhead", "the crane boom was slewing over the area",
        "a load was held on the sling", "pipe joints were being hoisted overhead",
        "the hydra crane was lifting a skid",
    ],
    "fall from height": [
        "work was being done at 6 metres", "the scaffold platform had an open edge",
        "personnel were on the monkey board", "a ladder was in use at height",
        "the elevated platform had an incomplete handrail",
    ],
    "kinetic (line of fire)": [
        "the pig launcher was under stored pressure",
        "a tensioned sling was under load", "the hose could whip if released",
        "a dropped object risk existed from the derrick",
        "the line was under tension across the walkway",
    ],
    "mechanical/rotating equipment": [
        "the pump shaft was rotating", "the coupling was turning without a guard",
        "the drawworks was in motion", "the belt drive was running",
        "the top drive was rotating",
    ],
    "vehicular/motion": [
        "a tanker was reversing in the yard", "the forklift was moving through the walkway",
        "a vehicle was manoeuvring in a blind spot",
        "heavy plant was moving through the pedestrian route",
    ],
    "atmospheric/asphyxiation": [
        "the vessel had been nitrogen purged", "the tank atmosphere was oxygen deficient",
        "H2S was possible in the sump", "the confined space had not been ventilated",
        "hydrogen sulphide levels were unknown",
    ],
    "chemical/toxic exposure": [
        "caustic was being decanted", "an acid drum was being handled",
        "biocide was being dosed into the line", "methanol was being transferred",
        "corrosive chemical splash was possible",
    ],
    "radiation (NORM/radiography)": [
        "radiography was in progress", "the iridium source was exposed",
        "NORM scale was present in the opened line",
        "gamma radiography was running on the adjacent weld",
    ],
    "defeated safety system": [
        "the ESD trip had been inhibited", "the gas detector was bypassed",
        "the high-level alarm was overridden", "the interlock was jumpered out",
        "the fire and gas loop was disabled for testing",
    ],
    "low-energy/ergonomic": [
        "housekeeping was poor in the walkway", "a minor oil spill was on the floor",
        "lighting was inadequate in the area", "materials were stacked untidily",
    ],
}

EXPOSURE_PHRASES: dict[str, list[str]] = {
    "direct_proximity": [
        "a worker was standing within the immediate hazard zone",
        "personnel were working inside the affected area",
        "two crew members were in the immediate work zone",
        "the technician was working at the point of exposure",
    ],
    "indirect_proximity": [
        "a worker was nearby but not directly in the hazard path",
        "personnel were in the general work area at the time",
        "the crew were about ten metres away behind the barricade",
        "another team was working on the adjacent deck",
        "staff were passing through the area intermittently",
        "two operators were nearby but outside the marked zone",
        "personnel were in the general work area, screened from the hazard",
        "the nearest worker was some fifteen metres away",
        "a contractor crew was working on the adjacent module",
        "people were moving through the area but not stopping at the job front",
        "the helper stood back from the work front while it was in progress",
    ],
    "no_exposure": [
        "no personnel were in the vicinity at the time",
        "the area was clear of workers during the activity",
        "the job was suspended before anyone entered the area",
        "work had not yet started and nobody was exposed",
        "the site had been evacuated before the activity commenced",
        "no one was present in the area for the duration of the task",
        "the work front was unmanned when the condition was observed",
        "all personnel had been withdrawn before the operation began",
    ],
}

# Energy-specific direct-exposure phrasings. A report about chemical dosing
# should not read "hands inside the guard opening" — an HSE reader notices that
# immediately, and so would a judge. Falls back to the generic pool above.
DIRECT_EXPOSURE_BY_ENERGY: dict[str, list[str]] = {
    "stored/electrical energy": [
        "personnel were within arm's reach of the live component",
        "the electrician had removed the panel cover with the feeder still live",
        "a worker was in contact with the enclosure while it was energised",
    ],
    "pressure/hydraulic energy": [
        "an operator was standing on the discharge side of the valve",
        "the fitter was directly in front of the flange being broken",
        "a worker was astride the pressurised line",
    ],
    "thermal (hot work)": [
        "the helper was standing in the path of falling sparks",
        "a worker was directly beside the cutting operation without screening",
        "personnel were working immediately below the hot work",
    ],
    "flammable/explosive atmosphere": [
        "personnel were standing downwind of the release",
        "a worker was inside the vapour cloud footprint",
        "the crew were working next to the leak source",
    ],
    "gravitational (suspended load)": [
        "the contractor was positioned directly beneath the suspended load",
        "the rigger was standing under the raised section",
        "a banksman was inside the swing radius of the load",
    ],
    "fall from height": [
        "the worker was at the open edge without being clipped on",
        "a technician was standing on the unprotected platform edge",
        "personnel were on the scaffold with the guardrail removed",
    ],
    "kinetic (line of fire)": [
        "two crew members were working in the line of fire",
        "a worker was standing in line with the tensioned sling",
        "the operator was directly in front of the closure being opened",
    ],
    "mechanical/rotating equipment": [
        "the fitter had his hands inside the guard opening",
        "a worker was adjusting the belt while it was still turning",
        "personnel were within reach of the exposed coupling",
    ],
    "vehicular/motion": [
        "a pedestrian was crossing directly behind the reversing vehicle",
        "a worker was standing in the blind spot of the moving plant",
        "personnel were walking in the vehicle route without segregation",
    ],
    "atmospheric/asphyxiation": [
        "a technician was inside the vessel when work commenced",
        "a worker had entered the confined space ahead of the entry check",
        "personnel were at the manway with their head inside the tank",
    ],
    "chemical/toxic exposure": [
        "the operator was decanting at arm's length without a face shield",
        "a worker was handling the drum with the bung already open",
        "personnel were in the splash zone during the transfer",
    ],
    "radiation (NORM/radiography)": [
        "a worker walked inside the cordoned radiography area",
        "personnel were within the marked dose-rate boundary",
        "a technician was working next to the exposed source",
    ],
    "defeated safety system": [
        "operations continued with personnel inside the protected zone",
        "a worker was in the area the disabled trip was meant to protect",
        "the crew kept working while the detection was inhibited",
    ],
    "low-energy/ergonomic": [
        "a worker walked through the affected walkway",
        "personnel were using the obstructed access route",
    ],
}

# Stated outcomes are deliberately DECOUPLED from the SIF label.
OUTCOME_PHRASES: list[str] = [
    "No injury occurred.",
    "No injury occurred; the worker moved away in time.",
    "Minor first aid case reported.",
    "Near miss - the situation was corrected before escalation.",
    "Reported as an unsafe condition during a routine walk-around.",
    "Work was stopped and the area made safe.",
    "No damage or injury resulted.",
    "The observation was raised at the next toolbox talk.",
    "A first aid dressing was applied at the site clinic.",
    "No loss event; reported for learning.",
    "The job was completed without incident after the observation.",
    "No consequence on this occasion.",
    "Condition rectified on the spot.",
    "Escalated to the area authority for follow-up.",
    "No harm; logged for trend analysis.",
    "The crew self-reported the condition at the end of shift.",
]

OBSERVER_ROLES = [
    "the HSE officer", "the shift supervisor", "the area authority",
    "a UA/UC observer", "the safety steward", "the field engineer",
    "the night shift in-charge", "the contractor HSE representative",
]

REPORTER_ROLES = [
    "hse_officer", "shift_supervisor", "field_engineer", "operator",
    "contractor_supervisor", "safety_steward", "area_authority",
]

TRAILING_NOTES = [
    " (PTW ref attached)", " acc to shift log", " reported via UA/UC card",
    " raised in the shift handover", " photo attached", "", "", "", "",
]

# --------------------------------------------------------------------------
# Field-entry noise
# --------------------------------------------------------------------------

ABBREV_SWAPS = {
    "permit to work": "PTW",
    "the lockout-tagout": "LOTO",
    "isolation": "LOTO",
    "personal protective equipment": "PPE",
    "hydrogen sulphide": "H2S",
    "job safety analysis": "JSA",
    "simultaneous operations": "SIMOPS",
    "atmospheric monitoring": "gas testing",
}

TYPO_SWAPS = {
    "supervisor": "supervsor",
    "confirmed": "confimed",
    "welding": "wielding",
    "maintenance": "maintainance",
    "excavation": "excavaton",
    "equipment": "equipmnt",
    "pressure": "presure",
    "barricading": "baricading",
    "isolation": "isolaton",
    "personnel": "personel",
    "immediate": "immediat",
    "scaffolding": "scafolding",
}

CODE_MIXED_INSERTS = [
    " Mazdoor ko turant hataya gaya.",
    " Supervisor ne bola area khali tha.",
    " Isolation ka check nahi kiya gaya tha.",
    " Kaam turant band karwaya gaya.",
    " Team ko dobara briefing di gayi.",
    " Permit site pe nahi mila.",
    " Gas test pehle shift me hua tha.",
]


def _apply_typos(text: str, rng: random.Random, rate: float) -> str:
    """Swap whole words for common field-entry misspellings."""
    if not text:
        return text
    out = text
    for correct, wrong in TYPO_SWAPS.items():
        if correct in out.lower() and rng.random() < rate:
            idx = out.lower().find(correct)
            out = out[:idx] + wrong + out[idx + len(correct):]
    return out


def _apply_abbrevs(text: str, rng: random.Random, rate: float) -> str:
    if not text:
        return text
    out = text
    for long_form, short in ABBREV_SWAPS.items():
        if long_form in out.lower() and rng.random() < rate:
            idx = out.lower().find(long_form)
            out = out[:idx] + short + out[idx + len(long_form):]
    return out


def _degrade(text: str, rng: random.Random, level: float) -> str:
    """Apply the full noise ladder to one segment. Segment-local so that
    character offsets stay computable after concatenation."""
    if not text or level <= 0:
        return text
    out = _apply_abbrevs(text, rng, level * 0.7)
    out = _apply_typos(out, rng, level * 0.5)
    if rng.random() < level * 0.25:
        out = out.upper() if rng.random() < 0.35 else out.lower()
    return out


# --------------------------------------------------------------------------
# Span-tracking text builder
# --------------------------------------------------------------------------


@dataclass
class Segment:
    text: str
    label: Optional[str] = None


@dataclass
class BuiltText:
    text: str
    spans: list[dict] = field(default_factory=list)


def build_text(segments: list[Segment]) -> BuiltText:
    """Concatenate segments, recording [start, end) offsets for labelled ones.

    Offsets are computed on the FINAL string, so they remain valid for the
    noisy text a model is actually given at inference time.
    """
    parts: list[str] = []
    spans: list[dict] = []
    cursor = 0
    for seg in segments:
        if not seg.text:
            continue
        start = cursor
        end = start + len(seg.text)
        if seg.label:
            spans.append({"label": seg.label, "text": seg.text, "span": [start, end]})
        parts.append(seg.text)
        cursor = end
    return BuiltText(text="".join(parts), spans=spans)


# --------------------------------------------------------------------------
# Report composition — several narrative shapes, not one template
# --------------------------------------------------------------------------


def _cap(text: str) -> str:
    return text[0].upper() + text[1:] if text else text


def _compose(
    rng: random.Random,
    activity: str,
    site: str,
    hazard: str,
    barrier_phrase: str,
    exposure_phrase: str,
    outcome: str,
    note: str,
    noise: float,
    terse: bool,
) -> BuiltText:
    """Assemble one report in one of several narrative shapes."""
    A = lambda t: Segment(_degrade(t, rng, noise), "ACTIVITY")   # noqa: E731
    L = lambda t: Segment(_degrade(t, rng, noise), "LOCATION")   # noqa: E731
    H = lambda t: Segment(_degrade(t, rng, noise), "HAZARD")     # noqa: E731
    B = lambda t: Segment(_degrade(t, rng, noise), "BARRIER")    # noqa: E731
    X = lambda t: Segment(_degrade(t, rng, noise), "EXPOSURE")   # noqa: E731
    P = lambda t: Segment(t)                                     # noqa: E731

    observer = rng.choice(OBSERVER_ROLES)

    if terse:
        # Extreme-brevity reports: real corpora are full of these.
        shape = rng.randint(0, 2)
        if shape == 0:
            segs = [A(activity), P(" - "), L(site), P(". "), H(_cap(hazard)), P(". ")]
            if barrier_phrase:
                segs += [B(_cap(barrier_phrase)), P(". ")]
            segs += [X(_cap(exposure_phrase)), P(".")]
        elif shape == 1:
            segs = [L(site), P(": "), A(activity), P(". ")]
            if barrier_phrase:
                segs += [B(_cap(barrier_phrase)), P(". ")]
            segs += [X(_cap(exposure_phrase)), P(". "), P(outcome)]
        else:
            segs = [A(_cap(activity)), P(" at "), L(site), P(". "), X(_cap(exposure_phrase)), P(". ")]
            if barrier_phrase:
                segs += [B(_cap(barrier_phrase)), P(".")]
        return build_text(segs)

    shape = rng.randint(0, 4)

    if shape == 0:
        segs = [
            P("During "), A(activity), P(" at "), L(site), P(", "),
            X(exposure_phrase), P(". "),
            H(_cap(hazard)), P(". "),
        ]
        if barrier_phrase:
            segs += [B(_cap(barrier_phrase)), P(". ")]
        segs += [P(outcome), P(note)]

    elif shape == 1:
        segs = [
            P("While carrying out "), A(activity), P(" at "), L(site), P(", "),
            P(observer), P(" observed that "), X(exposure_phrase), P(". "),
        ]
        if barrier_phrase:
            segs += [B(_cap(barrier_phrase)), P(", although "), H(hazard), P(". ")]
        else:
            segs += [H(_cap(hazard)), P(". ")]
        segs += [P(outcome), P(note)]

    elif shape == 2:
        segs = [
            L(_cap(site)), P(" - unsafe condition raised during "), A(activity), P(". "),
            H(_cap(hazard)), P(" and "), X(exposure_phrase), P(". "),
        ]
        if barrier_phrase:
            segs += [B(_cap(barrier_phrase)), P(". ")]
        segs += [P(outcome), P(note)]

    elif shape == 3:
        segs = [
            P("Observation logged by "), P(observer), P(" at "), L(site), P(". "),
            P("Task in progress: "), A(activity), P(". "),
        ]
        if barrier_phrase:
            segs += [B(_cap(barrier_phrase)), P("; "), H(hazard), P(". ")]
        else:
            segs += [H(_cap(hazard)), P(". ")]
        segs += [X(_cap(exposure_phrase)), P(". "), P(outcome), P(note)]

    else:
        segs = [
            P("Reported condition at "), L(site), P(" during "), A(activity), P(": "),
            H(hazard), P(". "),
        ]
        if barrier_phrase:
            segs += [B(_cap(barrier_phrase)), P(". ")]
        segs += [P("At the time, "), X(exposure_phrase), P(". "), P(outcome), P(note)]

    built = build_text(segs)
    return built


# --------------------------------------------------------------------------
# Ground truth — SCL decision logic
# --------------------------------------------------------------------------


def scl_label(energy_type: str, barrier_status: str, exposure: str, barrier_type: str) -> bool:
    """EEI SCL-style ground truth.

    Positive (SIF-potential / PSIF) when ALL hold:
      * a high-energy source is present (>= ~1500 J proxy), AND
      * a person was credibly exposed, AND
      * there was no *direct* control confirmed in place.

    A confirmed ADMINISTRATIVE control (permit, journey plan, lift plan) does
    not clear the exposure the way a confirmed ENGINEERING control does — this
    is the SCL "direct control" test, and it is what stops the corpus being
    trivially separable on the phrase "not confirmed".

    Deliberately independent of the stated outcome.
    """
    if not is_high_energy(energy_type):
        return False
    if exposure == "no_exposure":
        return False
    if barrier_status == "confirmed_present":
        return not bool(BARRIER_TYPES[barrier_type]["is_direct_control"])
    # uncertain / explicitly_absent / not_mentioned all count as "no direct
    # control confirmed" — absence of mention is never read as presence.
    return True


# --------------------------------------------------------------------------
# Planted patterns — give clustering / association mining / CUSUM real signal
# --------------------------------------------------------------------------


@dataclass
class PlantedPattern:
    pattern_id: str
    site: str
    activity: str
    energy_type: str
    barrier_status: str
    exposure: str
    count: int
    kind: str                 # established | emerging | sporadic_high_severity
    window: tuple[float, float]   # fraction of the timeline the pattern occupies


PLANTED_PATTERNS: list[PlantedPattern] = [
    # Established: steady across the whole year, several sites.
    PlantedPattern("p_isolation_handover", "Rig 7", "night shift handover at wellsite",
                   "stored/electrical energy", "uncertain", "direct_proximity",
                   260, "established", (0.0, 1.0)),
    PlantedPattern("p_isolation_maint", "Plant C", "maintenance on process equipment",
                   "stored/electrical energy", "uncertain", "direct_proximity",
                   220, "established", (0.0, 1.0)),
    PlantedPattern("p_lift_zone", "Rig 4", "lifting operation with mobile crane",
                   "gravitational (suspended load)", "explicitly_absent", "direct_proximity",
                   190, "established", (0.0, 1.0)),
    # Emerging: concentrated in the final quarter — this is what CUSUM must catch.
    PlantedPattern("p_sis_bypass", "Plant D", "gas compressor maintenance",
                   "defeated safety system", "explicitly_absent", "direct_proximity",
                   150, "emerging", (0.70, 1.0)),
    PlantedPattern("p_gastest_stale", "Terminal A", "confined space entry for tank cleaning",
                   "atmospheric/asphyxiation", "uncertain", "direct_proximity",
                   120, "emerging", (0.78, 1.0)),
    # Sporadic but severe: few reports, maximum energy, no barrier at all.
    PlantedPattern("p_pressure_rare", "Pipeline Section 9", "flowline pressure testing",
                   "pressure/hydraulic energy", "explicitly_absent", "direct_proximity",
                   14, "sporadic_high_severity", (0.0, 1.0)),
    PlantedPattern("p_radiography_rare", "Field Station 5", "radiography of pipeline welds",
                   "radiation (NORM/radiography)", "explicitly_absent", "direct_proximity",
                   9, "sporadic_high_severity", (0.35, 1.0)),
]


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------


def _sample_timestamp(rng: random.Random, start: datetime, days: int,
                      window: tuple[float, float] = (0.0, 1.0)) -> datetime:
    lo, hi = window
    frac = rng.uniform(lo, hi)
    offset_days = frac * days
    ts = start + timedelta(days=offset_days)
    # Field reports cluster in working hours with a night-shift tail.
    hour = rng.choice([6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 19, 22, 2])
    return ts.replace(hour=hour, minute=rng.randrange(60), second=0, microsecond=0)


def _make_report(
    rng: random.Random,
    *,
    site_rec: dict,
    activity: str,
    energy_type: str,
    barrier_status: str,
    exposure: str,
    timestamp: datetime,
    pattern_id: str = "",
    label_noise: float = 0.03,
) -> dict:
    site = site_rec["name"]
    barrier_type = ENERGY_TO_BARRIER.get(energy_type, "Permit to work")
    barrier_noun = rng.choice(BARRIER_NOUNS[barrier_type])
    barrier_phrase = rng.choice(BARRIER_TEMPLATES[barrier_status]).format(b=barrier_noun)
    hazard = rng.choice(HAZARD_PHRASES[energy_type])
    if exposure == "direct_proximity":
        # Prefer an energy-specific phrasing so the narrative stays coherent
        # (no "hands inside the guard" on a chemical-dosing report).
        pool = DIRECT_EXPOSURE_BY_ENERGY.get(energy_type, []) + EXPOSURE_PHRASES["direct_proximity"]
        exposure_phrase = rng.choice(pool)
    else:
        exposure_phrase = rng.choice(EXPOSURE_PHRASES[exposure])
    outcome = rng.choice(OUTCOME_PHRASES)
    note = rng.choice(TRAILING_NOTES)

    failure_mode = ""
    if barrier_status in ("uncertain", "explicitly_absent"):
        failure_mode = rng.choice(BARRIER_TYPES[barrier_type]["failure_modes"])

    # ---- ground truth (SCL logic, outcome-independent) ----
    truth = scl_label(energy_type, barrier_status, exposure, barrier_type)
    sif_potential = truth
    if rng.random() < label_noise:          # real corpora contain ambiguity
        sif_potential = not sif_potential
    lsr_tag = lsr_for(energy_type) if sif_potential else "N/A"

    # ---- surface realisation ----
    terse = rng.random() < 0.16
    noise = 0.0 if rng.random() < 0.35 else rng.uniform(0.15, 0.85)

    clean = _compose(rng, activity, site, hazard, barrier_phrase, exposure_phrase,
                     outcome, note, noise=0.0, terse=terse)
    noisy = _compose(rng, activity, site, hazard, barrier_phrase, exposure_phrase,
                     outcome, note, noise=noise, terse=terse)

    text = noisy.text
    spans = noisy.spans
    if noise > 0 and rng.random() < 0.35:
        insert = rng.choice(CODE_MIXED_INSERTS)
        text = text + insert          # appended, so existing spans stay valid

    # sanity: every recorded span must still slice back to its own text
    spans = [s for s in spans if text[s["span"][0]:s["span"][1]] == s["text"]]

    return {
        "report_id": uuid.UUID(int=rng.getrandbits(128)).hex[:8],
        "timestamp": timestamp.replace(tzinfo=timezone.utc).isoformat(),
        "site": site,
        "site_type": site_rec["type"],
        "region": site_rec["region"],
        "reporter_role": rng.choice(REPORTER_ROLES),
        "activity": activity,
        "energy_type": energy_type,
        "magnitude_class": magnitude_of(energy_type),
        "barrier_type": barrier_type,
        "barrier_status": barrier_status,
        "barrier_failure_mode": failure_mode,
        "is_direct_control": int(bool(BARRIER_TYPES[barrier_type]["is_direct_control"])),
        "exposure": exposure,
        "report_text": text,
        "report_text_clean": clean.text,
        "spans": json.dumps(spans, ensure_ascii=False),
        "stated_outcome": outcome,
        "sif_potential": int(sif_potential),
        "sif_potential_truth": int(truth),
        "lsr_tag": lsr_tag,
        "pattern_id": pattern_id,
        "source": "synthetic",
    }


def generate(n: int = 25000, seed: int = 42, months: int = 12) -> list[dict]:
    """Generate `n` synthetic UA/UC reports spanning the last `months` months."""
    rng = random.Random(seed)
    end = datetime(2026, 9, 1, tzinfo=timezone.utc)
    days = months * 30
    start = end - timedelta(days=days)
    start = start.replace(tzinfo=None)

    site_by_name = {s["name"]: s for s in SITES}
    rows: list[dict] = []

    # ---- 1. planted patterns first ----
    for pat in PLANTED_PATTERNS:
        for _ in range(pat.count):
            ts = _sample_timestamp(rng, start, days, pat.window)
            rows.append(_make_report(
                rng,
                site_rec=site_by_name[pat.site],
                activity=pat.activity,
                energy_type=pat.energy_type,
                barrier_status=pat.barrier_status,
                exposure=pat.exposure,
                timestamp=ts,
                pattern_id=pat.pattern_id,
                label_noise=0.01,   # planted patterns are cleaner by design
            ))

    # ---- 2. background corpus ----
    # Site report volume scales with workforce AND reporting culture, so the
    # density metric has a genuine reporting-culture confound to correct for.
    site_weights = [s["workforce"] * s["reporting_culture"] for s in SITES]
    remaining = max(0, n - len(rows))

    for _ in range(remaining):
        site_rec = rng.choices(SITES, weights=site_weights, k=1)[0]
        activity = rng.choice(ACTIVITIES)
        energy_type = rng.choice(ACTIVITY_ENERGY_MAP[activity])
        barrier_status = rng.choices(
            ["confirmed_present", "uncertain", "explicitly_absent", "not_mentioned"],
            weights=[0.42, 0.24, 0.18, 0.16],
        )[0]
        exposure = rng.choices(
            ["direct_proximity", "indirect_proximity", "no_exposure"],
            weights=[0.32, 0.38, 0.30],
        )[0]
        ts = _sample_timestamp(rng, start, days)
        rows.append(_make_report(
            rng,
            site_rec=site_rec,
            activity=activity,
            energy_type=energy_type,
            barrier_status=barrier_status,
            exposure=exposure,
            timestamp=ts,
        ))

    rng.shuffle(rows)
    return rows


__all__ = [
    "generate",
    "scl_label",
    "load_ontology",
    "is_high_energy",
    "lsr_for",
    "magnitude_of",
    "ONTOLOGY",
    "PLANTED_PATTERNS",
]
