"""OIL Site Registry & Location Normalization Engine.

Maintains canonical registries for:
1. Public OIL Asset Registry (real-world operational fields and facilities in Assam,
   Rajasthan, and Arunachal Pradesh)
2. Prototype / Synthetic Unit Registry (used for demonstration and evaluation datasets)
   explicitly labeled with 'is_synthetic_prototype: True' and demonstration flags.

Preserves exact raw-text character spans for UI highlighting.
"""

import re
from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class SiteInfo:
    site_id: str
    canonical_name: str
    region: str
    state: str
    facility_type: str
    latitude: float
    longitude: float
    is_synthetic_prototype: bool
    parent_asset: Optional[str] = None
    description: str = ""


# ---------------------------------------------------------------------------
# Canonical Site Registry
# ---------------------------------------------------------------------------
SITE_REGISTRY: dict[str, SiteInfo] = {
    # 1. Public OIL Operational Assets
    "duliajan": SiteInfo(
        site_id="duliajan",
        canonical_name="Duliajan",
        region="Upper Assam Basin",
        state="Assam",
        facility_type="Headquarters & Central Processing Facility",
        latitude=27.3587,
        longitude=95.3197,
        is_synthetic_prototype=False,
        description="OIL's operational headquarters, engineering workshops, and central processing hub.",
    ),
    "naharkatiya": SiteInfo(
        site_id="naharkatiya",
        canonical_name="Naharkatiya",
        region="Upper Assam Basin",
        state="Assam",
        facility_type="Producing Oilfield & Gas Gathering Hub",
        latitude=27.2833,
        longitude=95.3333,
        is_synthetic_prototype=False,
        description="Historic discovery field with mature artificial lift wells and compression manifolds.",
    ),
    "moran": SiteInfo(
        site_id="moran",
        canonical_name="Moran",
        region="Upper Assam Basin",
        state="Assam",
        facility_type="Producing Oilfield & Water Injection Facility",
        latitude=27.1856,
        longitude=94.9297,
        is_synthetic_prototype=False,
        description="Major onshore oilfield with extensive flowlines, gathering stations, and heavy workover operations.",
    ),
    "digboi": SiteInfo(
        site_id="digboi",
        canonical_name="Digboi",
        region="Upper Assam Basin",
        state="Assam",
        facility_type="Historic Field Area & Terminal",
        latitude=27.3800,
        longitude=95.6300,
        is_synthetic_prototype=False,
        description="Historic operational area with legacy flowlines, storage tanks, and pump stations.",
    ),
    "jorajan": SiteInfo(
        site_id="jorajan",
        canonical_name="Jorajan",
        region="Upper Assam Basin",
        state="Assam",
        facility_type="Oilfield & Well Gathering Station",
        latitude=27.4200,
        longitude=95.4500,
        is_synthetic_prototype=False,
        description="Active producing oilfield with multiple well clusters and testing headers.",
    ),
    "dandewala": SiteInfo(
        site_id="dandewala",
        canonical_name="Dandewala",
        region="Jaisalmer Basin",
        state="Rajasthan",
        facility_type="Gas Field & Dehydration Plant",
        latitude=27.1500,
        longitude=70.3000,
        is_synthetic_prototype=False,
        description="Desert gas extraction asset with high-pressure separators and dehydration manifolds.",
    ),
    "baghewala": SiteInfo(
        site_id="baghewala",
        canonical_name="Baghewala",
        region="Bikaner-Nagaur Basin",
        state="Rajasthan",
        facility_type="Heavy Oil Production Field",
        latitude=28.0100,
        longitude=73.3100,
        is_synthetic_prototype=False,
        description="Heavy crude recovery site operating cyclic steam stimulation and thermal equipment.",
    ),
    "kumchai": SiteInfo(
        site_id="kumchai",
        canonical_name="Kumchai",
        region="Arunachal Fold Belt",
        state="Arunachal Pradesh",
        facility_type="Hilly Terrain Oil & Gas Field",
        latitude=27.5000,
        longitude=96.0000,
        is_synthetic_prototype=False,
        description="Challenging terrain operation with elevated flowline crossings and remote wellheads.",
    ),
    "kusijan": SiteInfo(
        site_id="kusijan",
        canonical_name="Kusijan",
        region="Upper Assam Basin",
        state="Assam",
        facility_type="Oilfield & Flowline Gathering Node",
        latitude=27.3200,
        longitude=95.2500,
        is_synthetic_prototype=False,
        description="Producing field with multiple satellite gathering manifolds.",
    ),
    "shalmari": SiteInfo(
        site_id="shalmari",
        canonical_name="Shalmari",
        region="Upper Assam Basin",
        state="Assam",
        facility_type="Oilfield & Gas Lift Station",
        latitude=27.2500,
        longitude=95.1000,
        is_synthetic_prototype=False,
        description="Gas-lift enabled producing field with high-pressure gas distribution loops.",
    ),

    # 2. Prototype / Synthetic Demonstration Units
    "rig_4": SiteInfo(
        site_id="rig_4",
        canonical_name="Rig 4",
        region="Upper Assam Basin",
        state="Assam",
        facility_type="Onshore Heavy Drilling Rig",
        latitude=27.3650,
        longitude=95.3250,
        is_synthetic_prototype=True,
        parent_asset="duliajan",
        description="Synthetic demonstration unit: 1500 HP onshore drilling rig operating in Duliajan sector.",
    ),
    "rig_7": SiteInfo(
        site_id="rig_7",
        canonical_name="Rig 7",
        region="Upper Assam Basin",
        state="Assam",
        facility_type="Workover & Deep Drilling Rig",
        latitude=27.1920,
        longitude=94.9350,
        is_synthetic_prototype=True,
        parent_asset="moran",
        description="Synthetic demonstration unit: 2000 HP workover and deep drilling unit in Moran sector.",
    ),
    "plant_c": SiteInfo(
        site_id="plant_c",
        canonical_name="Plant C",
        region="Upper Assam Basin",
        state="Assam",
        facility_type="Central Gas Compression & LPG Plant",
        latitude=27.3520,
        longitude=95.3120,
        is_synthetic_prototype=True,
        parent_asset="duliajan",
        description="Synthetic demonstration unit: High-pressure gas boosting and separation plant.",
    ),
    "well_site_b": SiteInfo(
        site_id="well_site_b",
        canonical_name="Well Site B",
        region="Upper Assam Basin",
        state="Assam",
        facility_type="Multi-Well Cellar Pad",
        latitude=27.2900,
        longitude=95.3400,
        is_synthetic_prototype=True,
        parent_asset="naharkatiya",
        description="Synthetic demonstration unit: 4-well clustered cellar pad with manifold connections.",
    ),
    "field_station_2": SiteInfo(
        site_id="field_station_2",
        canonical_name="Field Station 2",
        region="Upper Assam Basin",
        state="Assam",
        facility_type="Field Gathering Station & Test Separator",
        latitude=27.4150,
        longitude=95.4450,
        is_synthetic_prototype=True,
        parent_asset="jorajan",
        description="Synthetic demonstration unit: Remote gathering station with flare header and oil pumps.",
    ),
    "terminal_a": SiteInfo(
        site_id="terminal_a",
        canonical_name="Terminal A",
        region="Upper Assam Basin",
        state="Assam",
        facility_type="Crude Oil Dispatch & Tank Farm",
        latitude=27.3750,
        longitude=95.6250,
        is_synthetic_prototype=True,
        parent_asset="digboi",
        description="Synthetic demonstration unit: Strategic crude dispatch terminal and pipeline intake.",
    ),
}

# ---------------------------------------------------------------------------
# Alias Mapping for Normalization & Exact Span Extraction
# ---------------------------------------------------------------------------
SITE_ALIASES: dict[str, str] = {
    # Public assets
    "duliajan": "duliajan",
    "duliajan hq": "duliajan",
    "duliajan field": "duliajan",
    "naharkatiya": "naharkatiya",
    "naharkatia": "naharkatiya",
    "nhk field": "naharkatiya",
    "moran": "moran",
    "moran field": "moran",
    "digboi": "digboi",
    "digboi field": "digboi",
    "jorajan": "jorajan",
    "jorajan field": "jorajan",
    "dandewala": "dandewala",
    "dandewala gas field": "dandewala",
    "baghewala": "baghewala",
    "baghewala oil field": "baghewala",
    "kumchai": "kumchai",
    "kusijan": "kusijan",
    "shalmari": "shalmari",

    # Synthetic prototypes
    "rig 4": "rig_4",
    "rig-4": "rig_4",
    "rig4": "rig_4",
    "rig 7": "rig_7",
    "rig-7": "rig_7",
    "rig7": "rig_7",
    "plant c": "plant_c",
    "plant-c": "plant_c",
    "plantc": "plant_c",
    "well site b": "well_site_b",
    "wellsite b": "well_site_b",
    "well-site-b": "well_site_b",
    "field station 2": "field_station_2",
    "field station-2": "field_station_2",
    "fs-2": "field_station_2",
    "terminal a": "terminal_a",
    "terminal-a": "terminal_a",
    "terminala": "terminal_a",
}


def resolve_site_from_text(raw_text: str) -> dict[str, Any]:
    """Scan raw text for known site aliases and return canonical site info and exact span.
    
    Returns:
        dict with:
            - site_id: str | None
            - canonical_name: str | None
            - span: tuple[int, int] | None
            - raw_match: str | None
            - confidence: float
            - is_synthetic_prototype: bool
            - site_info: SiteInfo | None
    """
    raw_lower = raw_text.lower()
    best_match: Optional[tuple[int, int, str, str]] = None

    # Sort aliases by length descending so longer phrases match first
    sorted_aliases = sorted(SITE_ALIASES.keys(), key=lambda k: len(k), reverse=True)

    for alias in sorted_aliases:
        pattern = r"\b" + re.escape(alias) + r"\b"
        match = re.search(pattern, raw_lower)
        if match:
            s_id = SITE_ALIASES[alias]
            span = (match.start(), match.end())
            raw_slice = raw_text[span[0]:span[1]]
            best_match = (span[0], span[1], s_id, raw_slice)
            break

    if best_match:
        start, end, site_id, raw_slice = best_match
        info = SITE_REGISTRY.get(site_id)
        return {
            "site_id": site_id,
            "canonical_name": info.canonical_name if info else site_id,
            "span": (start, end),
            "raw_match": raw_slice,
            "confidence": 0.95,
            "is_synthetic_prototype": info.is_synthetic_prototype if info else False,
            "site_info": info,
        }

    return {
        "site_id": None,
        "canonical_name": None,
        "span": None,
        "raw_match": None,
        "confidence": 0.0,
        "is_synthetic_prototype": False,
        "site_info": None,
    }


def normalize_site_name(name_or_alias: str) -> str:
    """Normalize any string name or alias into a canonical site name."""
    if not name_or_alias:
        return "Rig 4"
    cleaned = name_or_alias.strip().lower()
    if cleaned in SITE_ALIASES:
        s_id = SITE_ALIASES[cleaned]
        return SITE_REGISTRY[s_id].canonical_name
    for s_id, info in SITE_REGISTRY.items():
        if info.canonical_name.lower() == cleaned:
            return info.canonical_name
    return name_or_alias.strip()


def get_all_sites() -> list[dict[str, Any]]:
    """Return list of all registered sites formatted for API consumption."""
    return [
        {
            "site_id": info.site_id,
            "canonical_name": info.canonical_name,
            "region": info.region,
            "state": info.state,
            "facility_type": info.facility_type,
            "latitude": info.latitude,
            "longitude": info.longitude,
            "is_synthetic_prototype": info.is_synthetic_prototype,
            "parent_asset": info.parent_asset,
            "description": info.description,
            "demonstration_notice": "SYNTHETIC DEMONSTRATION DATA" if info.is_synthetic_prototype else "PUBLIC OIL ASSET",
        }
        for info in SITE_REGISTRY.values()
    ]


def get_site_by_id(site_id_or_name: str) -> Optional[dict[str, Any]]:
    """Look up a site by site_id or canonical name."""
    cleaned = site_id_or_name.strip().lower()
    # Check ID direct match
    if cleaned in SITE_REGISTRY:
        info = SITE_REGISTRY[cleaned]
        res = get_all_sites()
        return next(s for s in res if s["site_id"] == info.site_id)
    # Check aliases
    if cleaned in SITE_ALIASES:
        s_id = SITE_ALIASES[cleaned]
        info = SITE_REGISTRY[s_id]
        res = get_all_sites()
        return next(s for s in res if s["site_id"] == info.site_id)
    # Check canonical name
    for info in SITE_REGISTRY.values():
        if info.canonical_name.lower() == cleaned:
            res = get_all_sites()
            return next(s for s in res if s["site_id"] == info.site_id)
    return None
