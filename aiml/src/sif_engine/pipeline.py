"""End-to-End SIF Precursor Detection Pipeline Orchestrator.

Architecture:
Raw report
   ↓
Stage 0 preprocessing (abbreviations, code-mixed translation, typos, noise)
   ↓
Stage 1 evidence extraction (WHAT does the report say? Exact raw text spans)
   ├── Activity
   ├── Hazard
   ├── Exposure
   ├── Barrier + Barrier status (4 states, graded gap severity)
   └── Location (prototype/synthetic site vocabulary)
   ↓
Energy classifier (model vs fallback transparency, source tracking)
   ↓
Consistency validation (token contradiction detection, near-miss preservation)
   ↓
Stage 2 SCL reasoner (WHAT does that imply for SIF? SCL decision logic)
   ↓
SIF + LSR + plain-language justification
   ↓
Stage 3 confidence & review routing (HOW confident are we / who reviews it?)

Exposes:
  run_single(report_id: str, report_text: str, site: str = "Rig 4", model_name: Optional[str] = None) -> dict
  run_batch(reports: list[dict], model_name: Optional[str] = None) -> list[dict]
  get_model_status() -> dict
"""

from pathlib import Path
from typing import Any, Optional
import yaml

from sif_engine.preprocessing.pipeline import preprocess_report_with_metadata
from sif_engine.extraction.evidence_extractor import extract_evidence
from sif_engine.extraction.energy_classifier import classify_energy
from sif_engine.reasoning.consistency import validate_consistency
from sif_engine.reasoning.scl_reasoner import reason
from sif_engine.confidence.routing import route_prediction

_ONTOLOGY_DATA = None


def _load_ontology() -> dict[str, Any]:
    """Load configs/ontology.yaml safely."""
    global _ONTOLOGY_DATA
    if _ONTOLOGY_DATA is not None:
        return _ONTOLOGY_DATA
    config_path = Path(__file__).resolve().parent.parent.parent / "configs" / "ontology.yaml"
    if config_path.is_file():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                _ONTOLOGY_DATA = yaml.safe_load(f) or {}
                return _ONTOLOGY_DATA
        except Exception:
            pass
    _ONTOLOGY_DATA = {}
    return _ONTOLOGY_DATA


def _extract_heuristic_fields(text: str, lsr_tag: str) -> dict[str, Any]:
    """
    Stage 1 heuristic extraction:
    Scans raw text against the ontology and keywords for matched phrases and spans.
    Strictly calculates character spans against the EXACT original report text.
    Unsupported or unmatched fields are marked as unavailable/uncertain with span=None.
    """
    ontology = _load_ontology()
    lower_text = text.lower()
    evidence_spans: list[dict[str, Any]] = []

    # 1. Activity
    activity_text = "unspecified activity"
    activity_span = None
    activity_conf = 0.60
    for act in ontology.get("activities", []):
        m = re.search(re.escape(act.lower()), lower_text)
        if m:
            activity_span = (m.start(), m.end())
            activity_text = text[m.start():m.end()]
            activity_conf = 0.88
            evidence_spans.append({
                "field": "activity",
                "text": activity_text,
                "span": activity_span,
                "confidence": activity_conf,
            })
            break

    # 2. Hazard
    hazard_data = None
    hazard_terms = [
        "hazard zone", "live component", "suspended load", "h2s", "gas leak",
        "pressure release", "steam leak", "falling object", "rotating equipment",
        "fire", "electrical shock", "open flange", "unshielded", "toxic vapor",
    ]
    for haz in hazard_terms:
        m = re.search(r"\b" + re.escape(haz) + r"\b", lower_text)
        if m:
            h_span = (m.start(), m.end())
            h_text = text[m.start():m.end()]
            hazard_data = {
                "text": h_text,
                "span": h_span,
                "confidence": 0.85,
            }
            evidence_spans.append({
                "field": "hazard",
                "text": h_text,
                "span": h_span,
                "confidence": 0.85,
            })
            break

    # 3. Energy Type
    energy_label = "unspecified/general energy"
    energy_conf = 0.65
    energy_span = None
    for et, details in ontology.get("energy_types", {}).items():
        if details.get("lsr_tag", "").lower() == lsr_tag.lower():
            energy_label = et
            energy_conf = 0.85
            break
    # Optional direct keyword match for energy span
    energy_keywords = ["electrical", "stored energy", "high pressure", "thermal", "steam", "hydraulic", "gravity", "kinetic"]
    for ek in energy_keywords:
        m = re.search(r"\b" + re.escape(ek) + r"\b", lower_text)
        if m:
            energy_span = (m.start(), m.end())
            evidence_spans.append({
                "field": "energy_type",
                "text": text[m.start():m.end()],
                "span": energy_span,
                "confidence": 0.85,
            })
            break

    # 4. Barrier
    barrier_data = None
    barrier_terms = [
        "isolation", "permit to work", "ptw", "lockout", "tagout", "loto",
        "exclusion zone", "gas test", "scaffolding tag", "barrier tape",
        "guard rail", "interlock", "ventilation", "life line", "safety harness",
    ]
    for b_term in barrier_terms:
        m = re.search(r"\b" + re.escape(b_term) + r"\b", lower_text)
        if m:
            b_span = (m.start(), m.end())
            b_text = text[m.start():m.end()]
            barrier_data = {
                "text": b_text,
                "span": b_span,
                "confidence": 0.86,
            }
            evidence_spans.append({
                "field": "barrier",
                "text": b_text,
                "span": b_span,
                "confidence": 0.86,
            })
            break

    # 5. Barrier Status
    barrier_label = "uncertain"
    barrier_span = None
    barrier_conf = 0.70
    found_barrier = False
    for status_key, phrases in ontology.get("barrier_status_phrases", {}).items():
        for phrase in phrases:
            if phrase and phrase.lower() in lower_text:
                m = re.search(re.escape(phrase.lower()), lower_text)
                if m:
                    barrier_label = status_key
                    barrier_span = (m.start(), m.end())
                    barrier_conf = 0.86
                    evidence_spans.append({
                        "field": "barrier_status",
                        "text": text[m.start():m.end()],
                        "span": barrier_span,
                        "confidence": barrier_conf,
                    })
                    found_barrier = True
                    break
        if found_barrier:
            break

    # 6. Exposure
    exposure_label = "direct_proximity"
    exposure_span = None
    exposure_conf = 0.70
    found_exposure = False
    for exp_key, phrases in ontology.get("exposure_phrases", {}).items():
        for phrase in phrases:
            if phrase and phrase.lower() in lower_text:
                m = re.search(re.escape(phrase.lower()), lower_text)
                if m:
                    exposure_label = exp_key
                    exposure_span = (m.start(), m.end())
                    exposure_conf = 0.88
                    evidence_spans.append({
                        "field": "exposure",
                        "text": text[m.start():m.end()],
                        "span": exposure_span,
                        "confidence": exposure_conf,
                    })
                    found_exposure = True
                    break
        if found_exposure:
            break

    # 7. Location
    location_data = None
    location_terms = ontology.get("sites", []) + [
        "confined space", "tank", "vessel", "manifold", "rig floor", "deck",
        "warehouse", "cellar pit", "substructure", "derrick", "drilling floor",
    ]
    for loc in location_terms:
        m = re.search(r"\b" + re.escape(loc.lower()) + r"\b", lower_text)
        if m:
            loc_span = (m.start(), m.end())
            loc_text = text[m.start():m.end()]
            location_data = {
                "text": loc_text,
                "span": loc_span,
                "confidence": 0.88,
            }
            evidence_spans.append({
                "field": "location",
                "text": loc_text,
                "span": loc_span,
                "confidence": 0.88,
            })
            break

    return {
        "activity": {
            "text": activity_text,
            "span": activity_span,
            "confidence": activity_conf,
        },
        "hazard": hazard_data,
        "energy_type": {
            "label": energy_label,
            "confidence": energy_conf,
            "span": energy_span,
        },
        "exposure": {
            "label": exposure_label,
            "confidence": exposure_conf,
            "span": exposure_span,
        },
        "barrier": barrier_data,
        "barrier_status": {
            "label": barrier_label,
            "confidence": barrier_conf,
            "span": barrier_span,
        },
        "location": location_data,
        "evidence_spans": evidence_spans,
    }


def run_single(
    report_id: str,
    report_text: str,
    site: str = "Rig 4",
    model_name: Optional[str] = None,
) -> dict[str, Any]:
    """Run one raw report through the full 3-stage SIF detection pipeline."""
    raw_text = report_text or ""
    ontology = _load_ontology()
    activity_energy_map = ontology.get("activity_energy_map", {})
    ontology_activities = ontology.get("activities", [])

    # -----------------------------------------------------------------------
    # Stage 0: Preprocessing
    # -----------------------------------------------------------------------
    stage0_meta = preprocess_report_with_metadata(raw_text, lowercase=True)
    preprocessed_text = stage0_meta.get("preprocessed_text", raw_text)

    # -----------------------------------------------------------------------
    # Stage 1: Evidence Extraction (Raw text character spans)
    # -----------------------------------------------------------------------
    evidence = extract_evidence(raw_text, ontology_activities=ontology_activities)

    # Resolve location: priority to extracted location if found in report
    extracted_loc = evidence.get("location", {})
    resolved_site = extracted_loc.get("value") or site

    # Extract contextual safety environment (17 categories, exact raw spans, negation-aware)
    from sif_engine.extraction.environment_extractor import extract_environment
    from sif_engine.site_intelligence.site_registry import normalize_site_name, get_site_by_id
    environment_result = extract_environment(raw_text)
    resolved_canonical_site = normalize_site_name(resolved_site)
    site_metadata = get_site_by_id(resolved_canonical_site)

    # Extract hazard category
    hazard_info = evidence.get("hazard", {})
    best_hazard = hazard_info.get("best_category")

    # -----------------------------------------------------------------------
    # Energy Classification (with model vs fallback transparency & rule gate)
    # -----------------------------------------------------------------------
    energy_classification = classify_energy(
        raw_text=raw_text,
        preprocessed_text=preprocessed_text,
        hazard_category=best_hazard,
        model_name=model_name,
    )

    # -----------------------------------------------------------------------
    # Stage 1 Consistency Validation
    # -----------------------------------------------------------------------
    consistency_result = validate_consistency(
        evidence=evidence,
        energy_classification=energy_classification,
        activity_energy_map=activity_energy_map,
    )

    # -----------------------------------------------------------------------
    # Stage 2: SCL Reasoner (Authoritative Reasoning Engine)
    # -----------------------------------------------------------------------
    reasoner_result = reason(
        evidence=evidence,
        energy_classification=energy_classification,
        consistency_result=consistency_result,
    )

    sif_potential = reasoner_result["sif_potential"]
    barrier_status = reasoner_result["barrier_status"]
    candidate_needs_info = reasoner_result["candidate_needs_info"]
    decision_factors = reasoner_result["decision_factors"]

    # -----------------------------------------------------------------------
    # Stage 3: Confidence Calibration & 4-Bucket Routing
    # -----------------------------------------------------------------------
    base_confidence = energy_classification.get("confidence", 0.70)
    bucket, calibrated_confidence = route_prediction(
        sif_potential=sif_potential,
        base_confidence=base_confidence,
        decision_factors=decision_factors,
        consistency_result=consistency_result,
        barrier_status=barrier_status,
        candidate_needs_info=candidate_needs_info,
    )

    # -----------------------------------------------------------------------
    # Assemble Extracted Fields with exact raw-text spans
    # -----------------------------------------------------------------------
    # Activity span
    act_data = evidence.get("activity", {})
    activity_field = {
        "text": act_data.get("text", "unspecified activity"),
        "span": act_data.get("span"),
        "confidence": act_data.get("confidence", 0.50),
    }


    energy_field = {
        "label": energy_classification.get("label", "unspecified energy"),
        "confidence": energy_classification.get("confidence", 0.70),
        "span": None,
    }

    # Barrier span
    barrier_data = evidence.get("barrier")
    barrier_span = None
    barrier_text = ""
    if barrier_data and barrier_data.evidence:
        barrier_span = barrier_data.evidence[0].span
        barrier_text = barrier_data.evidence[0].text

    barrier_field = {
        "text": barrier_text,
        "confidence": getattr(barrier_data, "confidence", 0.80) if barrier_data else 0.70,
        "span": barrier_span,
    }
    barrier_status_field = {
        "label": barrier_status,
        "confidence": getattr(barrier_data, "confidence", 0.80) if barrier_data else 0.70,
        "span": barrier_span,
    }

    # Exposure span
    exp_data = evidence.get("exposure", {})
    exposure_field = {
        "label": exp_data.get("label", "unspecified"),
        "confidence": exp_data.get("confidence", 0.75),
        "span": exp_data.get("span"),
    }

    # Hazard span
    hazard_field = None
    if best_hazard:
        first_hazard = hazard_info["matches"][best_hazard][0]
        hazard_field = {
            "text": first_hazard.text,
            "confidence": 0.85,
            "span": first_hazard.span,
        }

    # Location span
    location_field = None
    if extracted_loc.get("value"):
        location_field = {
            "text": extracted_loc["value"],
            "span": extracted_loc["span"],
            "confidence": extracted_loc.get("confidence", 0.95),
        }

    # Contextual Safety Environment field
    environment_field = {
        "category": environment_result.get("category"),
        "text": environment_result.get("text"),
        "span": environment_result.get("span"),
        "confidence": environment_result.get("confidence", 0.0),
        "negated": environment_result.get("negated", False),
        "provenance": environment_result.get("provenance", "none"),
        "all_detected": environment_result.get("all_detected", []),
    }

    # Keep all extracted evidence in raw-text coordinates for audit and UI use.
    evidence_spans = []
    if act_data.get("span"):
        evidence_spans.append({
            "field": "activity",
            "text": act_data["text"],
            "span": act_data["span"],
            "confidence": act_data.get("confidence", 0.80),
        })
    for match in hazard_info.get("matches", {}).values():
        for item in match:
            evidence_spans.append({
                "field": "hazard",
                "text": item.text,
                "span": item.span,
                "confidence": 0.85,
            })
    for item in exp_data.get("evidence", []):
        evidence_spans.append({
            "field": "exposure",
            "text": item.text,
            "span": item.span,
            "confidence": exp_data.get("confidence", 0.75),
        })
    if barrier_data:
        for item in barrier_data.evidence:
            evidence_spans.append({
                "field": "barrier_status",
                "text": item.text,
                "span": item.span,
                "confidence": getattr(barrier_data, "confidence", 0.70),
            })
    if extracted_loc.get("value"):
        evidence_spans.append({
            "field": "location",
            "text": extracted_loc["value"],
            "span": extracted_loc["span"],
            "confidence": extracted_loc.get("confidence", 0.95),
        })
    if environment_result.get("span"):
        evidence_spans.append({
            "field": "environment",
            "text": environment_result["text"],
            "span": environment_result["span"],
            "confidence": environment_result.get("confidence", 0.80),
        })

    extracted_fields = {
        "activity": activity_field,
        "energy_type": energy_field,
        "barrier_status": barrier_status_field,
        "exposure": exposure_field,
        "hazard": hazard_field,
        "barrier": barrier_field if barrier_data and barrier_data.evidence else None,
        "location": location_field,
        "environment": environment_field,
        "evidence_spans": evidence_spans,
    }

    model_ver = energy_classification.get(
        "model_version",
        "rule-fallback-v0.1" if energy_classification.get("source") == "fallback" else "baseline2-v0.3",
    )
    classification = {
        "sif_potential": sif_potential,
        "confidence": calibrated_confidence,
        "bucket": bucket,
        "lsr_tag": reasoner_result["lsr_tag"],
        "justification": reasoner_result["justification"],
        "model_version": model_ver,
    }

    structured_reasoning = {
        "activity": {
            "text": act_data.get("text", "unspecified activity"),
            "span": act_data.get("span"),
            "confidence": act_data.get("confidence", 0.5),
        },
        "hazard": {
            "best_category": best_hazard,
            "matches": hazard_info.get("matches", {}),
            "text": hazard_field.get("text") if hazard_field else None,
            "span": hazard_field.get("span") if hazard_field else None,
        },
        "primary_hazard": reasoner_result.get("primary_hazard", best_hazard),
        "secondary_hazards": reasoner_result.get("secondary_hazards", []),
        "energy": {
            "label": energy_classification.get("label", "unspecified energy"),
            "is_high_energy": decision_factors.get("is_high_energy", False),
            "source": energy_classification.get("high_energy_source", energy_classification.get("source", "fallback")),
            "confidence": energy_classification.get("confidence", 0.7),
            "high_energy_confidence": energy_classification.get("high_energy_confidence", 0.7),
            "high_energy_evidence": energy_classification.get("high_energy_evidence", []),
        },
        "exposure": exposure_field,
        "barrier": {
            "status": reasoner_result.get("barrier_status", barrier_status),
            "gap_severity": reasoner_result.get("barrier_gap_severity"),
            "evidence": barrier_data.evidence if barrier_data and barrier_data.evidence else [],
            "legacy_label": barrier_status,
        },
        "environment": environment_field,
        "credible_consequence": reasoner_result.get("credible_consequence", {}),
        "sif_potential": sif_potential,
        "lsr": {
            "rule": reasoner_result.get("lsr_tag", "unresolved"),
            "reason": reasoner_result.get("credible_consequence", {}).get("description", "No ontology rule matched the current evidence."),
            "confidence": 0.75 if reasoner_result.get("lsr_tag") not in [None, "N/A", "Other"] else 0.0,
            "ontology_source": "rule_engine",
        },
        "missing_information": [],
        "contradictions": reasoner_result.get("contradictions_detected", []),
        "evidence": [
            {"field": item["field"], "text": item["text"], "span": item["span"], "confidence": item.get("confidence", 0.8)}
            for item in evidence_spans
        ],
        "reasoning_steps": [
            {"step": 1, "label": "Activity", "detail": f"Activity identified: {act_data.get('text', 'unspecified activity')}"},
            {"step": 2, "label": "Hazard / Energy", "detail": f"Energy: {energy_classification.get('label', 'unspecified energy')}"},
            {"step": 3, "label": "Exposure", "detail": f"Exposure: {exposure_field.get('label', 'unspecified')}"},
            {"step": 4, "label": "Barrier", "detail": f"Barrier: {reasoner_result.get('barrier_status', barrier_status)}"},
            {"step": 5, "label": "Credible consequence", "detail": reasoner_result.get("credible_consequence", {}).get("primary_consequence", "No consequence mapped")},
            {"step": 6, "label": "SIF potential", "detail": "SIF potential likely" if sif_potential else "No SIF pathway supported by current evidence"},
            {"step": 7, "label": "LSR", "detail": reasoner_result.get("lsr_tag", "unresolved")},
        ],
        "provenance": {
            "energy_source": energy_classification.get("high_energy_source", energy_classification.get("source", "fallback")),
            "barrier_source": "raw_text_evidence",
            "model_version": model_ver,
            "source": "structured_reasoning_engine",
        },
        "confidence": calibrated_confidence,
        "bucket": bucket,
        "lsr_tag": reasoner_result["lsr_tag"],
        "credible_consequence_legacy": reasoner_result.get("credible_consequence", {}),
        "barrier_status": barrier_status,
        "barrier_gap_severity": reasoner_result.get("barrier_gap_severity"),
        "exposure_mode": exposure_field.get("label"),
        "candidate_needs_info": candidate_needs_info,
        "contradictions_detected": reasoner_result.get("contradictions_detected", []),
        "audit_justification": reasoner_result["justification"],
        "decision_factors": decision_factors,
    }

    return {
        "report_id": report_id,
        "site": resolved_canonical_site,
        "report_text": raw_text,
        "extracted_fields": extracted_fields,
        "classification": classification,
        "reasoning": structured_reasoning,
        "site_intelligence": {
            "site_id": site_metadata["site_id"] if site_metadata else resolved_canonical_site.lower().replace(" ", "_"),
            "canonical_name": resolved_canonical_site,
            "region": site_metadata["region"] if site_metadata else "Upper Assam Basin",
            "state": site_metadata["state"] if site_metadata else "Assam",
            "facility_type": site_metadata["facility_type"] if site_metadata else "Operational Facility",
            "latitude": site_metadata["latitude"] if site_metadata else 27.3587,
            "longitude": site_metadata["longitude"] if site_metadata else 95.3197,
            "is_synthetic_prototype": site_metadata.get("is_synthetic_prototype", True) if site_metadata else True,
            "demonstration_notice": "SYNTHETIC DEMONSTRATION DATA" if (site_metadata and site_metadata.get("is_synthetic_prototype")) else "PUBLIC OIL ASSET",
        },
        "preprocessed_text": preprocessed_text,
        "stage_metadata": {
            "stage0": stage0_meta,
            "consistency": consistency_result,
            "decision_factors": decision_factors,
        },
    }



def run_batch(
    reports: list[dict[str, Any]],
    model_name: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Run a batch of reports through the end-to-end multi-stage pipeline."""
    results = []
    for r in reports:
        report_id = r.get("report_id") or "rep_unknown"
        report_text = r.get("report_text") or ""
        site = r.get("site") or "Rig 4"
        res = run_single(
            report_id=report_id,
            report_text=report_text,
            site=site,
            model_name=model_name,
        )
        results.append(res)
    return results


def get_model_status() -> dict[str, Any]:
    """Return runtime metadata about the active SIF models."""
    try:
        from sif_engine.inference.model_registry import get_model_metadata
        return get_model_metadata()
    except Exception:
        return {
            "model_version": "baseline2-v0.3",
            "active_sif_model": "baseline2",
            "mlp_available": True,
            "available_models": ["baseline2", "mlp"],
        }