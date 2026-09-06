"""
End-to-end orchestrator:
Takes raw report text, runs Stage 0 (preprocessing), applies Stage 1
structured extraction (heuristic ontology-matching with marked provisional
placeholders until the fine-tuned transformer is complete), and executes
Stage 2 / Stage 3 classification using the active model artifact
(Baseline 2 by default, or MLP benchmark).

Exposes:
  run_single(report_id: str, report_text: str, site: str = "Rig 4", model_name: Optional[str] = None) -> dict
  run_batch(reports: list[dict], model_name: Optional[str] = None) -> list[dict]
  get_model_status() -> dict
"""

import re
from pathlib import Path
from typing import Any, Optional
import yaml

from sif_engine.inference.model_registry import (
    get_active_model,
    get_model,
    get_model_metadata,
)

_ONTOLOGY_DATA = None


def _load_ontology() -> dict[str, Any]:
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
    Scans text against the ontology for matched phrases and spans.
    Marked as heuristic/provisional until Stage 1 transformer NER model is trained.
    """
    ontology = _load_ontology()
    lower_text = text.lower()

    # 1. Activity
    activity_text = "general industrial activity"
    activity_span = (0, min(len(text), 30))
    activity_conf = 0.60
    for act in ontology.get("activities", []):
        m = re.search(re.escape(act.lower()), lower_text)
        if m:
            activity_text = text[m.start():m.end()]
            activity_span = (m.start(), m.end())
            activity_conf = 0.88
            break

    # 2. Energy Type
    energy_label = "unspecified/general energy"
    energy_conf = 0.65
    energy_span = None
    for et, details in ontology.get("energy_types", {}).items():
        if details.get("lsr_tag", "").lower() == lsr_tag.lower():
            energy_label = et
            energy_conf = 0.85
            break

    # 3. Barrier Status
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
                    found_barrier = True
                    break
        if found_barrier:
            break

    # 4. Exposure
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
                    found_exposure = True
                    break
        if found_exposure:
            break

    return {
        "activity": {
            "text": activity_text,
            "span": activity_span,
            "confidence": activity_conf,
        },
        "energy_type": {
            "label": energy_label,
            "confidence": energy_conf,
            "span": energy_span,
        },
        "barrier_status": {
            "label": barrier_label,
            "confidence": barrier_conf,
            "span": barrier_span,
        },
        "exposure": {
            "label": exposure_label,
            "confidence": exposure_conf,
            "span": exposure_span,
        },
    }


def run_single(
    report_id: str,
    report_text: str,
    site: str = "Rig 4",
    model_name: Optional[str] = None,
) -> dict[str, Any]:
    """Run one report through preprocessing and real classification inference."""
    model = get_model(model_name) if model_name else get_active_model()
    pred_result = model.predict(report_text)

    extracted_fields = _extract_heuristic_fields(report_text, pred_result["lsr_tag"])

    classification = {
        "sif_potential": pred_result["sif_potential"],
        "confidence": pred_result["confidence"],
        "bucket": pred_result["bucket"],
        "lsr_tag": pred_result["lsr_tag"],
        "justification": pred_result["justification"],
        "model_version": pred_result["model_version"],
    }

    return {
        "report_id": report_id,
        "site": site,
        "report_text": report_text,
        "extracted_fields": extracted_fields,
        "classification": classification,
        "preprocessed_text": pred_result.get("preprocessed_text"),
    }


def run_batch(
    reports: list[dict[str, Any]],
    model_name: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Run a batch of reports through the end-to-end pipeline."""
    results = []
    for r in reports:
        report_id = r.get("report_id") or "rep_unknown"
        report_text = r.get("report_text") or ""
        site = r.get("site") or "Rig 4"
        res = run_single(report_id=report_id, report_text=report_text, site=site, model_name=model_name)
        results.append(res)
    return results


def get_model_status() -> dict[str, Any]:
    """Return runtime metadata about the loaded and available SIF models."""
    return get_model_metadata()