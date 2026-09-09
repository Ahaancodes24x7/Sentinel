"""Ontology-Driven Credible Consequence Engine for SIF Precursor Assessment.

Evaluates plausible physical consequences if barriers fail and personnel are exposed.
Per IOGP / EEI SCL guidelines, a SIF precursor requires a realistic potential for
fatality or permanent disabling injury given the energy magnitude and exposure mode.

Pathways:
1. Suspended Load / Mechanical Lifting -> Crushed by falling object, blunt force trauma (LSR: Safe Mechanical Lifting)
2. Electrical / Stored Energy -> Electrocution, arc flash thermal burns, cardiac arrest (LSR: Energy Isolation)
3. Hot Work / Open Flame -> Vapor ignition, explosion, severe thermal burns (LSR: Hot Work)
4. Confined Space -> Atmospheric asphyxiation, H2S toxicity, loss of consciousness (LSR: Confined Space)
5. Working at Height -> Fatal fall from elevation, spinal/polytrauma (LSR: Working at Height)
6. Driving / Mobile Equipment -> Pedestrian strike, vehicle rollover, crushing (LSR: Driving)
7. Line of Fire / High Pressure -> Pressure burst, projectile strike, severe laceration (LSR: Line of Fire)
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ConsequencePathway:
    pathway_id: str
    energy_type: str
    lsr_tag: str
    potential_severity: str           # "fatality" | "life_altering_injury" | "recordable_only"
    is_sif_capable: bool
    credible_scenarios: list[str]
    required_barriers: list[str]
    description: str


# ---------------------------------------------------------------------------
# Canonical Credible Consequence Ontology
# ---------------------------------------------------------------------------
CREDIBLE_PATHWAYS: dict[str, ConsequencePathway] = {
    "suspended_load": ConsequencePathway(
        pathway_id="suspended_load",
        energy_type="gravitational (suspended load)",
        lsr_tag="Safe Mechanical Lifting",
        potential_severity="fatality",
        is_sif_capable=True,
        credible_scenarios=[
            "Dropped load crushing worker beneath",
            "Rigging failure causing swinging impact trauma",
            "Boom failure in lifting corridor"
        ],
        required_barriers=["Exclusion zone", "Certified rigging", "Lift plan sign-off"],
        description="Gravitational potential energy of suspended masses exceeding 500 kg capable of instantaneous crush fatality.",
    ),
    "electrical_isolation": ConsequencePathway(
        pathway_id="electrical_isolation",
        energy_type="stored/electrical energy",
        lsr_tag="Energy Isolation",
        potential_severity="fatality",
        is_sif_capable=True,
        credible_scenarios=[
            "Electrocution from direct contact with live 415V/high-voltage conductor",
            "Arc flash blast causing fatal third-degree burns and blast overpressure",
            "Induced voltage shock causing secondary fatal fall"
        ],
        required_barriers=["LOTO isolation", "Test-before-touch verification", "Arc-rated PPE"],
        description="Electrical shock potential exceeding lethal threshold (50V AC / 50mA) or arc flash incident energy.",
    ),
    "hot_work_ignition": ConsequencePathway(
        pathway_id="hot_work_ignition",
        energy_type="thermal (hot work)",
        lsr_tag="Hot Work",
        potential_severity="fatality",
        is_sif_capable=True,
        credible_scenarios=[
            "Ignition of hydrocarbon gas/vapor cloud causing flash fire",
            "Welding spark into combustible line causing process explosion",
            "Catastrophic vessel burn-through"
        ],
        required_barriers=["Hot work permit", "Continuous gas monitoring", "Fire watch"],
        description="Thermal energy ignition source in hydrocarbon processing environments capable of explosion or severe burns.",
    ),
    "confined_space_asphyxiation": ConsequencePathway(
        pathway_id="confined_space_asphyxiation",
        energy_type="atmospheric/asphyxiation",
        lsr_tag="Confined Space",
        potential_severity="fatality",
        is_sif_capable=True,
        credible_scenarios=[
            "Rapid atmospheric asphyxiation in oxygen-deficient enclosure (<19.5% O2)",
            "Acute toxic inhalation of H2S at lethal concentration (>100 ppm)",
            "Engulfment by trapped sludge or liquid"
        ],
        required_barriers=["Multi-gas testing sign-off", "Continuous forced ventilation", "Standby attendant"],
        description="Confined atmosphere capable of incapacitating entrant within seconds without prior warning.",
    ),
    "fall_from_height": ConsequencePathway(
        pathway_id="fall_from_height",
        energy_type="fall from height",
        lsr_tag="Working at Height",
        potential_severity="fatality",
        is_sif_capable=True,
        credible_scenarios=[
            "Free fall from elevated structure or derrick (>1.8m) causing fatal polytrauma",
            "Scaffold platform collapse with unharnessed workers",
            "Fall through unprotected grating or open cellar hatch"
        ],
        required_barriers=["100% tie-off harness", "Certified green-tagged scaffold", "Guardrails and toe boards"],
        description="Elevated work potential energy where impact velocity exceeds survivable deceleration threshold.",
    ),
    "vehicular_impact": ConsequencePathway(
        pathway_id="vehicular_impact",
        energy_type="vehicular/motion",
        lsr_tag="Driving",
        potential_severity="fatality",
        is_sif_capable=True,
        credible_scenarios=[
            "Heavy oilfield tanker striking pedestrian in terminal yard",
            "Rig moving equipment rollover on unpaved lease road",
            "Forklift collision or mast collapse"
        ],
        required_barriers=["Traffic management plan", "Banksman / spotter", "Speed enforcement"],
        description="Kinetic energy of heavy machinery exceeding impact tolerance of human torso.",
    ),
    "line_of_fire_burst": ConsequencePathway(
        pathway_id="line_of_fire_burst",
        energy_type="kinetic (line of fire)",
        lsr_tag="Line of Fire",
        potential_severity="life_altering_injury",
        is_sif_capable=True,
        credible_scenarios=[
            "High-pressure hydraulic/water line rupture causing projectile or fluid injection",
            "Recoil of parted mooring or winch line",
            "Rotating pipe tongs strike in derrick floor"
        ],
        required_barriers=["Whip checks / safety clamps", "Barricaded exclusion radius", "Shielded guards"],
        description="High-velocity release of kinetic energy or pressurized fluid causing penetrating trauma.",
    ),
    "stored_pressure_release": ConsequencePathway(
        pathway_id="stored_pressure_release",
        energy_type="stored pressure energy",
        lsr_tag="Energy Isolation",
        potential_severity="fatality",
        is_sif_capable=True,
        credible_scenarios=[
            "Unexpected hydraulic or pneumatic release causing injection or crush injury",
            "Pressure vessel or process line rupture causing blast and projectile trauma",
            "Stored energy release during maintenance causing fatal struck-by injury",
        ],
        required_barriers=["Energy isolation", "Depressurization and drain-down", "Test-before-work verification"],
        description="Stored hydraulic, pneumatic, or pressure energy can release without warning and cause fatal trauma.",
    ),
    "excavation_collapse": ConsequencePathway(
        pathway_id="excavation_collapse",
        energy_type="excavation collapse hazard",
        lsr_tag="N/A",
        potential_severity="fatality",
        is_sif_capable=True,
        credible_scenarios=[
            "Trench or excavation wall collapse causing burial and asphyxiation",
            "Underground service strike causing fire, explosion, or electrocution",
            "Engulfment of a worker in an unsupported excavation",
        ],
        required_barriers=["Engineered shoring or benching", "Underground service survey", "Safe setback and access"],
        description="Excavation hazards can cause fatal collapse or underground service strike; no specific LSR is forced.",
    ),
}


def evaluate_credible_consequence(
    energy_type: str,
    hazard_category: Optional[str] = None,
    exposure_label: str = "unspecified",
) -> dict[str, Any]:
    """Evaluate credible consequences based on physical energy type and exposure mode.
    
    Returns:
        dict with:
            - is_sif_capable: bool
            - potential_severity: str
            - primary_consequence: str
            - lsr_tag: str
            - credible_scenarios: list[str]
            - required_barriers: list[str]
            - description: str
    """
    # Map energy type or hazard to pathway
    pathway_key = None
    energy_lower = (energy_type or "").lower()
    if hazard_category == "excavation":
        pathway_key = "excavation_collapse"
    elif any(term in energy_lower for term in ["hydraulic", "pneumatic", "pressure", "stored energy"]):
        pathway_key = "stored_pressure_release"
    elif "suspended" in energy_lower or hazard_category == "safe_mechanical_lifting":
        pathway_key = "suspended_load"
    elif "electrical" in energy_type.lower() or hazard_category == "energy_isolation":
        pathway_key = "electrical_isolation"
    elif "hot work" in energy_type.lower() or "thermal" in energy_type.lower() or hazard_category == "hot_work":
        pathway_key = "hot_work_ignition"
    elif "confined" in energy_type.lower() or "asphyxiation" in energy_type.lower() or hazard_category == "confined_space":
        pathway_key = "confined_space_asphyxiation"
    elif "height" in energy_type.lower() or "fall" in energy_type.lower() or hazard_category == "working_at_height":
        pathway_key = "fall_from_height"
    elif "vehicular" in energy_type.lower() or "motion" in energy_type.lower() or hazard_category == "driving":
        pathway_key = "vehicular_impact"
    elif "line of fire" in energy_type.lower() or "kinetic" in energy_type.lower() or hazard_category == "line_of_fire":
        pathway_key = "line_of_fire_burst"

    if pathway_key and pathway_key in CREDIBLE_PATHWAYS:
        pathway = CREDIBLE_PATHWAYS[pathway_key]
        has_exposure = exposure_label in ["direct_proximity", "indirect_proximity"]
        
        return {
            "is_sif_capable": pathway.is_sif_capable and has_exposure,
            "potential_severity": pathway.potential_severity if has_exposure else "negligible_no_exposure",
            "primary_consequence": pathway.credible_scenarios[0] if pathway.credible_scenarios else "Severe injury",
            "lsr_tag": pathway.lsr_tag,
            "credible_scenarios": pathway.credible_scenarios,
            "required_barriers": pathway.required_barriers,
            "description": pathway.description,
            "pathway_id": pathway.pathway_id,
        }

    # Low-energy / ergonomic or unspecified
    return {
        "is_sif_capable": False,
        "potential_severity": "first_aid_or_minor",
        "primary_consequence": "Minor ergonomic strain or superficial abrasion",
        "lsr_tag": "Work Authorisation",
        "credible_scenarios": ["Slip, trip or ergonomic strain with no high-energy release"],
        "required_barriers": ["Housekeeping", "Standard PPE"],
        "description": "Activity involves low energy with no credible potential for fatal or permanent life-altering outcome.",
        "pathway_id": "low_energy",
    }
