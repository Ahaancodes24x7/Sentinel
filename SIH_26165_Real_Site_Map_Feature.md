# PS 26165 / Sentinel — Real-Site Map Feature

## 1. Real OIL India operating locations (research-grounded, sourced)

OIL India's own site (oil-india.com) states operations are organized into **Eastern, Western, and Central Assets** across Assam and Arunachal Pradesh, plus a **Rajasthan Fields** asset processed at Bhaghewala EPS and Dandewala GPC. Below is a real, sourced location list for the prototype map — **coordinates below are town/region-level approximations from public sources, not surveyed facility coordinates**, and should be labeled as such in the UI (a small "approximate location" badge is enough — don't imply GPS-precise facility positions we don't actually have).

| Site name | State | Type | Approx. coordinates | Source basis |
|---|---|---|---|---|
| Duliajan | Assam | OIL India Fields HQ | 27.3667°N, 95.3167°E | Wikipedia (exact, sourced) |
| Digboi | Assam | Historic oilfield + refinery | ~27.38°N, 95.62°E | Multiple public sources (oldest oilfield in India, 1889) |
| Moran | Assam | Oilfield (discovered 1956) | ~26.65°N, 94.85°E | Public oilfield references |
| Naharkatiya | Assam | Oilfield (since 1954) | ~27.28°N, 95.33°E | Public oilfield references, near Digboi |
| Kharsang | Arunachal Pradesh | JV field (with GeoEnpro) | ~27.33°N, 95.85°E | oil-india.com domestic footprint page |
| Barmer (Rajasthan Fields) | Rajasthan | Processing: Bhaghewala EPS, Dandewala GPC | ~25.75°N, 71.38°E | oil-india.com production page (town-level approx.) |

**Important framing for the demo:** these six names and states are real. The *incident reports* tied to them in this prototype remain 100% synthetic — the map should carry the same "Synthetic Demonstration Data" badge already used elsewhere in the dashboard (per the frontend spec's Section 3.4 guardrail), applied per-marker, not just once at the top of the screen, since a map is exactly the kind of visual that makes data feel more "real" than it is.

## 2. Data file for the frontend/backend to consume

```json
[
  {"site_id": "duliajan", "name": "Duliajan", "state": "Assam", "type": "fields_hq", "lat": 27.3667, "lon": 95.3167},
  {"site_id": "digboi", "name": "Digboi", "state": "Assam", "type": "oilfield", "lat": 27.38, "lon": 95.62},
  {"site_id": "moran", "name": "Moran", "state": "Assam", "type": "oilfield", "lat": 26.65, "lon": 94.85},
  {"site_id": "naharkatiya", "name": "Naharkatiya", "state": "Assam", "type": "oilfield", "lat": 27.28, "lon": 95.33},
  {"site_id": "kharsang", "name": "Kharsang", "state": "Arunachal Pradesh", "type": "jv_field", "lat": 27.33, "lon": 95.85},
  {"site_id": "barmer", "name": "Barmer (Rajasthan Fields)", "state": "Rajasthan", "type": "processing", "lat": 25.75, "lon": 71.38}
]
```

Save this as `aiml/configs/sites.yaml`-equivalent (or `.json`) — **the same single-source-of-truth principle as `ontology.yaml`**: the synthetic data generator, the backend, and the frontend should all read site names from this one file, not hardcode "Rig 4" / "Plant C" style placeholders in three different places (which is what the synthetic generator currently does — swap `SITES = ["Rig 4", "Rig 7", ...]` in `generate_synthetic_data.py` for real names drawn from this file, so the whole pipeline is consistent end to end).

## 3. Backend changes needed

### New endpoint: `GET /api/v1/sites`
```json
{
  "sites": [
    {"site_id": "duliajan", "name": "Duliajan", "state": "Assam", "type": "fields_hq",
     "lat": 27.3667, "lon": 95.3167, "is_real_location": true}
  ]
}
```
`is_real_location: true` on every entry — this flag is what lets the frontend show the "real location, synthetic data" badge without hardcoding that logic client-side.

### Modify `GET /dashboard/rankings`
Add `lat`/`lon` to each `RankingRow` (join against the new sites table by `group` name) so the existing ranking dashboard (Backend Spec Section 3) can feed the map directly — **no new ranking logic needed, just enrichment of the existing response.**

```json
{"group": "Duliajan", "sif_flagged_count": 18, "total_reports": 98, "density": 0.184,
 "trend_direction": "up", "trend_pct": 45.0, "primary_lsr": "Energy Isolation",
 "lat": 27.3667, "lon": 95.3167}
```

## 4. Frontend: the map screen

This is a **7th dashboard screen**, additive to the 6 already specified (Backend Spec's frontend section) — call it the **Site Map View**.

- Base map (Leaflet + OpenStreetMap tiles, or Mapbox if the team has a key) centered on India's northeast + a Rajasthan inset, since OIL's real footprint is genuinely split across two non-adjacent regions — don't force a single zoomed view that hides one cluster.
- Marker per site, sized/colored by the same precursor-density metric as the ranking dashboard (reuse, don't reinvent, the color scale from `dashboard/rankings`).
- Marker click → same Report Detail View / cluster drill-down already built, filtered to that site — this screen is a geographic *lens* onto data you already have, not a new data model.
- Persistent badge per marker popup: *"Real OIL India operating location — incident data shown is synthetic prototype data."*
- Toggle: "Assam/Arunachal cluster" vs. "Rajasthan cluster" vs. "All", since the two regions are ~2,500km apart and a single map view at a sensible zoom level for one hides the other.

## 5. What this does NOT claim

- No claim that these are OIL's *only* sites, or their precise facility boundaries — the six locations above are illustrative and sourced from public production/profile pages, not an operational site register.
- No claim that Mangala/Bhagyam/Aishwariya fields belong to OIL India — those are **Cairn India/Vedanta-operated** fields in the same Barmer basin; OIL India's own Rajasthan asset is the Bhaghewala EPS/Dandewala GPC processing operation specifically. Keeping this distinction straight matters if a judge with domain knowledge looks at the map.
- No real incident/safety data — every report plotted remains synthetic, exactly as everywhere else in this prototype.
