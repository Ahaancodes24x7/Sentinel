"""Demo camera & safety-zone registry for Camera Watch.

IMPORTANT — data honesty:
Camera identifiers here (DUL-C01, DIG-C01, MOR-C01, ...) are DEMONSTRATION
placeholders that drive the MVP UI so the team can show the feature working
per real OIL India site. They are NOT a claim that OIL India has installed
cameras with these IDs, or that Sentinel has an authorized live feed. A real
deployment would populate this registry from the site's actual CCTV/NVR
inventory instead of this fixed dict.

ROI polygons are given in normalized (0..1) coordinates so they render
correctly regardless of the source video's resolution or aspect ratio, and
are grouped by `roi_type` so the hazard-rule layer (hazard_rules.py) can stay
generic: "restricted_zone" and "lifting_zone" trigger a zone-entry rule for
any person whose ground point falls inside them, "vehicle_lane" is
descriptive/visual only today (proximity is evaluated directly between people
and vehicles, not by lane membership).

Zones are only one of the hazard families this system watches for. Fire,
smoke, loss of visibility, falls and falling masses are detected from the
scene itself and need no configuration at all, so a camera with no zones
defined is still fully monitored for the disaster precursors that matter.
"""
from __future__ import annotations

from typing import Optional

# Zone geometry note - why these are small and cornered rather than large:
# zone membership is tested at the persons GROUND POINT (bottom-centre of the
# box), so a zone that covers most of the frame fires on anyone standing
# anywhere and the console fills with alarms nobody reads. Keeping each zone
# to a bounded region of the view is what makes a zone alarm mean something.
_RESTRICTED_ZONE = {
    "name": "Restricted Zone",
    "roi_type": "restricted_zone",
    "points": [[0.62, 0.10], [0.95, 0.10], [0.95, 0.52], [0.62, 0.52]],
    "hazard_context": "energised electrical / process equipment area",
    "lsr_tag": "Energy Isolation",
}
_LIFTING_ZONE = {
    "name": "Lifting Exclusion Zone",
    "roi_type": "lifting_zone",
    "points": [[0.06, 0.58], [0.38, 0.58], [0.38, 0.92], [0.06, 0.92]],
    "hazard_context": "mechanical lifting / suspended load",
    "lsr_tag": "Safe Mechanical Lifting",
}
_VEHICLE_LANE = {
    "name": "Haul Road / Vehicle Lane",
    "roi_type": "vehicle_lane",
    "points": [[0.0, 0.86], [1.0, 0.86], [1.0, 1.0], [0.0, 1.0]],
    "hazard_context": "mobile plant and vehicle movement corridor",
    "lsr_tag": "Line of Fire",
}
_DEFAULT_ROIS = [_RESTRICTED_ZONE, _LIFTING_ZONE, _VEHICLE_LANE]

# site_id here matches sif_engine.site_intelligence.site_registry's canonical
# ids for the three real OIL India locations used in the SIH demo.
CAMERA_REGISTRY: dict[str, dict] = {
    "DUL-C01": {"camera_name": "Duliajan - Process Area Camera 1", "site_id": "duliajan"},
    "DUL-C02": {"camera_name": "Duliajan - Yard Camera 2", "site_id": "duliajan"},
    "DIG-C01": {"camera_name": "Digboi - Terminal Camera 1", "site_id": "digboi"},
    "DIG-C02": {"camera_name": "Digboi - Pump Station Camera 2", "site_id": "digboi"},
    "MOR-C01": {"camera_name": "Moran - Wellpad Camera 1", "site_id": "moran"},
    "MOR-C02": {"camera_name": "Moran - Gathering Station Camera 2", "site_id": "moran"},
}


def _camera_dict(camera_id: str, meta: dict) -> dict:
    return {
        "camera_id": camera_id,
        "camera_name": meta["camera_name"],
        "site_id": meta["site_id"],
        "rois": [dict(roi) for roi in _DEFAULT_ROIS],
    }


def get_cameras_for_site(site_id: str) -> list[dict]:
    site_id = (site_id or "").strip().lower()
    return [
        _camera_dict(cam_id, meta)
        for cam_id, meta in CAMERA_REGISTRY.items()
        if meta["site_id"] == site_id
    ]


def get_all_cameras() -> list[dict]:
    return [_camera_dict(cam_id, meta) for cam_id, meta in CAMERA_REGISTRY.items()]


def get_camera(camera_id: str) -> Optional[dict]:
    meta = CAMERA_REGISTRY.get(camera_id)
    if not meta:
        return None
    return _camera_dict(camera_id, meta)
