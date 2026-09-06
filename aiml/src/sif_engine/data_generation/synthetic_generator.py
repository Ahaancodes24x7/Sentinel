"""Synthetic UA/UC report generator for SIH PS 26165."""

import random
import uuid

from .ontology import ACTIVITIES, ACTIVITY_ENERGY_MAP, BARRIER_STATUS_PHRASES, ENERGY_TYPES, EXPOSURE_PHRASES, OUTCOME_PHRASES, SITES, high_energy, lsr_for

random.seed(42)
NOISE_SNIPPETS = [" (PTW ref attached)", " - LOTO tag #{}".format(random.randint(100, 999)), " acc to shift log", " reported by UA/UC observer", "", "", ""]
ABBREV_SWAPS = {"permit to work": "PTW", "permit": "PTW", "isolation": "LOTO", "supervisor": "supervsor", "confirmed": "confimed", "welding": "wielding", "maintenance": "maintainance", "excavation": "excavaton"}
CODE_MIXED_INSERTS = [" Mazdoor ko turant hataya gaya.", " Supervsor ne bola area khali tha.", " Check nahi kiya gaya tha isolation ka."]


def inject_field_noise(text: str, noise_rate: float = 0.5) -> str:
    """Inject realistic abbreviations, typos, and code-mixed phrases."""
    if random.random() > noise_rate:
        return text
    out = text
    for key, value in ABBREV_SWAPS.items():
        index = out.lower().find(key)
        if index != -1:
            out = out[:index] + value + out[index + len(key):]
    if random.random() < 0.4:
        out += random.choice(CODE_MIXED_INSERTS)
    return out


def make_report(i: int) -> dict:
    activity = random.choice(ACTIVITIES)
    energy_type = random.choice(ACTIVITY_ENERGY_MAP[activity])
    barrier_status = random.choices(["confirmed_present", "uncertain", "absent_not_mentioned"], weights=[0.45, 0.30, 0.25])[0]
    exposure = random.choices(["direct_proximity", "indirect_proximity", "no_exposure"], weights=[0.35, 0.35, 0.30])[0]
    site = random.choice(SITES)
    barrier_phrase = random.choice(BARRIER_STATUS_PHRASES[barrier_status])
    exposure_phrase = random.choice(EXPOSURE_PHRASES[exposure])
    sif_potential = bool(high_energy(energy_type) and barrier_status != "confirmed_present" and exposure != "no_exposure")
    lsr_tag = lsr_for(energy_type) if sif_potential else "N/A"
    if random.random() < 0.04:
        sif_potential = not sif_potential
    text_parts = [f"During {activity} at {site}, {exposure_phrase}.", f"{barrier_phrase[0].upper() + barrier_phrase[1:]}." if barrier_phrase else "", f"{random.choice(OUTCOME_PHRASES)}{random.choice(NOISE_SNIPPETS)}"]
    report_text_clean = " ".join(part for part in text_parts if part)
    return {"report_id": str(uuid.uuid4())[:8], "site": site, "activity": activity, "energy_type": energy_type, "barrier_status": barrier_status, "exposure": exposure, "report_text_clean": report_text_clean, "report_text": inject_field_noise(report_text_clean, noise_rate=0.55), "sif_potential": int(sif_potential), "lsr_tag": lsr_tag, "source": "synthetic"}


def generate(n=3000):
    return [make_report(i) for i in range(n)]