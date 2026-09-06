"""CLI entry point for generating clearly labeled synthetic reports."""

"""
Synthetic UA/UC (Unsafe Act / Unsafe Condition) report generator
for SIH PS 26165 — SIF Precursor Detection.

IMPORTANT: This generates SYNTHETIC data only. It is NOT real OIL India data.
It exists so the team has a realistic, labeled corpus to build and evaluate
the first AI/ML model against, before any real OIL data is available.

Ground-truth labeling logic follows the EEI SCL Model reasoning:
  SIF-potential = high_energy(energy_type)
                  AND barrier_status != 'confirmed_present'
                  AND exposure != 'no_exposure'
This deliberately does NOT depend on whether an injury occurred — matching
the core insight of the whole project (actual severity != fatal potential).
"""

import random
import json
import csv
import uuid
from pathlib import Path

random.seed(42)

# ---------------------------------------------------------------------------
# 1. ONTOLOGY  (this table is the seed for the Stage-2 rule engine too)
# ---------------------------------------------------------------------------

ACTIVITIES = [
    "maintenance on process equipment",
    "hot work / welding near process line",
    "lifting operation with mobile crane",
    "confined space entry for tank cleaning",
    "vehicle movement within plant premises",
    "excavation near buried utility line",
    "electrical panel work",
    "scaffolding erection at height",
    "pipeline pigging operation",
    "routine equipment inspection",
]

# energy_type -> (is_high_energy, primary LSR tag)
ENERGY_TYPES = {
    "stored/electrical energy":        (True,  "Energy Isolation"),
    "thermal (hot work)":              (True,  "Hot Work"),
    "gravitational (suspended load)":  (True,  "Safe Mechanical Lifting"),
    "kinetic (line of fire)":          (True,  "Line of Fire"),
    "atmospheric/asphyxiation":        (True,  "Confined Space"),
    "vehicular/motion":                (True,  "Driving"),
    "fall from height":                (True,  "Working at Height"),
    "low-energy/ergonomic":            (False, "Work Authorisation"),
}

# activity -> plausible energy types (keeps generated text realistic)
ACTIVITY_ENERGY_MAP = {
    "maintenance on process equipment": ["stored/electrical energy", "low-energy/ergonomic"],
    "hot work / welding near process line": ["thermal (hot work)", "stored/electrical energy"],
    "lifting operation with mobile crane": ["gravitational (suspended load)", "kinetic (line of fire)"],
    "confined space entry for tank cleaning": ["atmospheric/asphyxiation", "low-energy/ergonomic"],
    "vehicle movement within plant premises": ["vehicular/motion"],
    "excavation near buried utility line": ["stored/electrical energy", "low-energy/ergonomic"],
    "electrical panel work": ["stored/electrical energy"],
    "scaffolding erection at height": ["fall from height", "gravitational (suspended load)"],
    "pipeline pigging operation": ["stored/electrical energy", "kinetic (line of fire)"],
    "routine equipment inspection": ["low-energy/ergonomic", "stored/electrical energy"],
}

BARRIER_STATUS_PHRASES = {
    "confirmed_present": [
        "isolation was verified and tagged before work began",
        "exclusion zone was established and maintained throughout",
        "permit to work was signed off with all checks completed",
        "gas test was conducted and confirmed safe prior to entry",
    ],
    "uncertain": [
        "isolation status was not clearly confirmed by the crew",
        "exclusion zone markers were present but not actively enforced",
        "permit was raised but supervisor sign-off could not be located",
        "gas test reportedly done earlier in the shift, not re-verified",
    ],
    "absent_not_mentioned": [
        "no isolation was mentioned in the report",
        "no exclusion zone was set up",
        "work proceeded without a permit being sighted",
        "",  # nothing mentioned at all — realistic sparse reporting
    ],
}

EXPOSURE_PHRASES = {
    "direct_proximity": [
        "a worker was standing within the immediate hazard zone",
        "the contractor was positioned directly beneath the suspended load",
        "personnel were within arm's reach of the live component",
        "a technician was inside the equipment when work commenced",
    ],
    "indirect_proximity": [
        "a worker was nearby but not directly in the hazard path",
        "personnel were in the general work area at the time",
    ],
    "no_exposure": [
        "no personnel were in the vicinity at the time",
        "the area was clear of workers during the activity",
    ],
}

OUTCOME_PHRASES = [
    "No injury occurred.",
    "No injury occurred; worker moved away in time.",
    "Minor first aid case reported.",
    "Near miss — situation was corrected before escalation.",
    "Reported as unsafe condition during routine walk-around.",
]

SITES = ["Rig 4", "Rig 7", "Plant C", "Well Site B", "Field Station 2", "Terminal A"]

# a small pool of jargon/typo insertions to simulate real field-entered text
NOISE_SNIPPETS = [
    " (PTW ref attached)", " - LOTO tag #{}".format(random.randint(100, 999)),
    " acc to shift log", " reported by UA/UC observer", "", "", "",
]

# Realistic field-entry noise: abbreviations, code-mixed Hindi phrases, and
# common typos, injected probabilistically so preprocessing (Stage 0) has
# real, measurable work to do rather than a strawman.
ABBREV_SWAPS = {
    "permit to work": "PTW",
    "permit": "PTW",
    "isolation": "LOTO",
    "supervisor": "supervsor",   # typo variant
    "confirmed": "confimed",     # typo variant
    "welding": "wielding",       # typo variant
    "maintenance": "maintainance",  # typo variant
    "excavation": "excavaton",   # typo variant
}
CODE_MIXED_INSERTS = [
    " Mazdoor ko turant hataya gaya.",
    " Supervsor ne bola area khali tha.",
    " Check nahi kiya gaya tha isolation ka.",
]


def inject_field_noise(text: str, noise_rate: float = 0.5) -> str:
    """Simulate realistic messy field-entered report text: jargon
    abbreviations, typos, and occasional code-mixed Hindi phrasing.
    Applied to a random subset of reports (not all — real corpora are a mix
    of careful and hurried reporters). Swaps ALL matching candidate words
    (not just one or two) so the noise consistently affects the
    barrier/energy vocabulary the rule-based classifier depends on --
    otherwise the effect is diluted across many possible swap targets and
    the raw-vs-preprocessed comparison understates preprocessing's value."""
    if random.random() > noise_rate:
        return text
    out = text
    for k, v in ABBREV_SWAPS.items():
        idx = out.lower().find(k)
        if idx != -1:
            out = out[:idx] + v + out[idx + len(k):]
    if random.random() < 0.4:
        out = out + random.choice(CODE_MIXED_INSERTS)
    return out


def high_energy(energy_type: str) -> bool:
    return ENERGY_TYPES[energy_type][0]


def lsr_for(energy_type: str) -> str:
    return ENERGY_TYPES[energy_type][1]


def make_report(i: int) -> dict:
    activity = random.choice(ACTIVITIES)
    energy_type = random.choice(ACTIVITY_ENERGY_MAP[activity])
    barrier_status = random.choices(
        ["confirmed_present", "uncertain", "absent_not_mentioned"],
        weights=[0.45, 0.30, 0.25],
    )[0]
    exposure = random.choices(
        ["direct_proximity", "indirect_proximity", "no_exposure"],
        weights=[0.35, 0.35, 0.30],
    )[0]
    site = random.choice(SITES)
    outcome = random.choice(OUTCOME_PHRASES)
    barrier_phrase = random.choice(BARRIER_STATUS_PHRASES[barrier_status])
    exposure_phrase = random.choice(EXPOSURE_PHRASES[exposure])
    noise = random.choice(NOISE_SNIPPETS)

    # ---- ground truth label: SCL-style logic, NOT based on outcome text ----
    sif_potential = bool(
        high_energy(energy_type)
        and barrier_status != "confirmed_present"
        and exposure != "no_exposure"
    )
    lsr_tag = lsr_for(energy_type) if sif_potential else "N/A"

    # small chance of label noise to simulate real-world ambiguity (~4%)
    if random.random() < 0.04:
        sif_potential = not sif_potential

    text_parts = [
        f"During {activity} at {site}, {exposure_phrase}.",
        f"{barrier_phrase[0].upper() + barrier_phrase[1:]}." if barrier_phrase else "",
        f"{outcome}{noise}",
    ]
    report_text_clean = " ".join(p for p in text_parts if p)
    report_text_raw = inject_field_noise(report_text_clean, noise_rate=0.55)

    return {
        "report_id": str(uuid.uuid4())[:8],
        "site": site,
        "activity": activity,
        "energy_type": energy_type,
        "barrier_status": barrier_status,
        "exposure": exposure,
        "report_text_clean": report_text_clean,   # ground-truth phrasing, no noise
        "report_text": report_text_raw,           # what the model actually sees (noisy/messy)
        "sif_potential": int(sif_potential),
        "lsr_tag": lsr_tag,
        "source": "synthetic",
    }


def generate(n=3000):
    return [make_report(i) for i in range(n)]


if __name__ == "__main__":
    data = generate(3000)
    fieldnames = list(data[0].keys())
    base_dir = Path(__file__).resolve().parent.parent
    out_file = base_dir / "data" / "synthetic" / "synthetic_uauc_reports.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"Generated {len(data)} synthetic reports at {out_file}.")
    print("SIF-potential rate:", sum(d["sif_potential"] for d in data) / len(data))
