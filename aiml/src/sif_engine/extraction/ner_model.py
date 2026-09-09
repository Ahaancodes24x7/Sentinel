"""Fine-tuned transformer NER for safety-event span extraction.

Extracts five entity types from free-text UA/UC reports:

    ACTIVITY   what was being done
    HAZARD     the energy source / hazardous condition described
    BARRIER    the control mentioned (or its explicit absence)
    EXPOSURE   proximity / timing cues placing a person at risk
    LOCATION   the site

Why span-level NER rather than asking a large model to summarise the report:
a span is a stable, inspectable extraction unit a reviewer can accept or
correct token-by-token, and it aggregates cleanly into the structured event
store the dashboard and clustering layer read from. A free-text summary is
harder to correct, harder to aggregate, and impossible to score with span F1.

The model is optional at runtime. When no fine-tuned artefact is present,
:func:`extract_spans` falls back to the deterministic rule/gazetteer extractor
and says so via the ``source`` field — the pipeline degrades in quality but
never silently reports transformer output it did not produce.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Optional

ENTITY_TYPES = ["ACTIVITY", "HAZARD", "BARRIER", "EXPOSURE", "LOCATION"]

# BIO tag scheme
LABELS = ["O"] + [f"{p}-{e}" for e in ENTITY_TYPES for p in ("B", "I")]
LABEL2ID = {label: i for i, label in enumerate(LABELS)}
ID2LABEL = {i: label for label, i in LABEL2ID.items()}

BASE_MODEL = "distilbert-base-uncased"
MODEL_DIR = Path(__file__).resolve().parents[3] / "models" / "ner"

_pipeline = None
_load_attempted = False
_lock = threading.Lock()


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def _load_pipeline():
    """Lazily load the fine-tuned token-classification pipeline."""
    global _pipeline, _load_attempted
    if _load_attempted:
        return _pipeline
    with _lock:
        if _load_attempted:
            return _pipeline
        _load_attempted = True
        if not (MODEL_DIR / "config.json").is_file():
            return None
        try:
            from transformers import (
                AutoModelForTokenClassification,
                AutoTokenizer,
                pipeline as hf_pipeline,
            )

            tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
            model = AutoModelForTokenClassification.from_pretrained(str(MODEL_DIR))
            _pipeline = hf_pipeline(
                "token-classification",
                model=model,
                tokenizer=tokenizer,
                aggregation_strategy="simple",
            )
        except Exception:
            _pipeline = None
    return _pipeline


def model_available() -> bool:
    return _load_pipeline() is not None


def model_info() -> dict[str, Any]:
    meta_path = MODEL_DIR / "sentinel_meta.json"
    info: dict[str, Any] = {
        "available": model_available(),
        "model_dir": str(MODEL_DIR),
        "base_model": BASE_MODEL,
        "entity_types": ENTITY_TYPES,
    }
    if meta_path.is_file():
        try:
            info.update(json.loads(meta_path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return info


# --------------------------------------------------------------------------
# Inference
# --------------------------------------------------------------------------


def _rule_fallback(text: str) -> dict[str, Any]:
    """Deterministic extraction when no transformer artefact is available."""
    try:
        from sif_engine.extraction.evidence_extractor import extract_evidence

        ev = extract_evidence(text)
        spans: list[dict[str, Any]] = []
        for item in ev.get("evidence_spans", []) or []:
            label = str(item.get("field", "")).upper()
            mapping = {
                "ACTIVITY": "ACTIVITY", "HAZARD": "HAZARD", "BARRIER": "BARRIER",
                "BARRIER_STATUS": "BARRIER", "EXPOSURE": "EXPOSURE",
                "LOCATION": "LOCATION",
            }
            if label not in mapping:
                continue
            span = item.get("span")
            if not span:
                continue
            spans.append({
                "label": mapping[label],
                "text": item.get("text", ""),
                "span": [int(span[0]), int(span[1])],
                "confidence": float(item.get("confidence", 0.7)),
            })
        return {"spans": spans, "source": "rule_fallback"}
    except Exception:
        return {"spans": [], "source": "unavailable"}


def extract_spans(text: str, min_score: float = 0.35) -> dict[str, Any]:
    """Extract labelled character spans from ``text``.

    Returns ``{"spans": [{label, text, span:[start,end], confidence}, ...],
    "source": "transformer"|"rule_fallback"|"unavailable"}``.

    Offsets index into the ORIGINAL ``text`` so the frontend can highlight
    directly without re-tokenising.
    """
    text = text or ""
    if not text.strip():
        return {"spans": [], "source": "empty_input"}

    pipe = _load_pipeline()
    if pipe is None:
        return _rule_fallback(text)

    try:
        raw = pipe(text)
    except Exception:
        return _rule_fallback(text)

    spans: list[dict[str, Any]] = []
    for ent in raw:
        score = float(ent.get("score", 0.0))
        if score < min_score:
            continue
        start, end = int(ent["start"]), int(ent["end"])
        if end <= start:
            continue
        label = str(ent.get("entity_group", "")).upper()
        if label not in ENTITY_TYPES:
            continue
        spans.append({
            "label": label,
            "text": text[start:end],
            "span": [start, end],
            "confidence": round(score, 4),
        })
    spans.sort(key=lambda s: s["span"][0])
    return {"spans": spans, "source": "transformer"}


def extract_fields(text: str) -> dict[str, Any]:
    """Convenience view: highest-confidence span per entity type."""
    result = extract_spans(text)
    best: dict[str, Any] = {}
    for span in result["spans"]:
        label = span["label"].lower()
        if label not in best or span["confidence"] > best[label]["confidence"]:
            best[label] = span
    return {"fields": best, "source": result["source"], "spans": result["spans"]}


# --------------------------------------------------------------------------
# Training data preparation
# --------------------------------------------------------------------------


def spans_to_bio(text: str, spans: list[dict], tokenizer, max_length: int = 256):
    """Align character spans onto wordpiece tokens, producing BIO label ids.

    Uses the fast tokenizer's ``offset_mapping``. Special tokens and any token
    that does not overlap a labelled span get -100 so they are ignored by the
    loss.
    """
    encoding = tokenizer(
        text,
        truncation=True,
        max_length=max_length,
        return_offsets_mapping=True,
    )
    offsets = encoding["offset_mapping"]
    labels = []
    for idx, (start, end) in enumerate(offsets):
        if start == end:                      # special token
            labels.append(-100)
            continue
        tag = "O"
        for span in spans:
            s, e = span["span"]
            if start >= s and end <= e:
                tag = f"B-{span['label']}" if start == s else f"I-{span['label']}"
                break
            # partial overlap (tokenizer boundary differs from phrase boundary)
            if start < e and end > s:
                tag = f"B-{span['label']}" if start <= s else f"I-{span['label']}"
                break
        labels.append(LABEL2ID.get(tag, 0))
    encoding.pop("offset_mapping")
    encoding["labels"] = labels
    return encoding


__all__ = [
    "extract_spans",
    "extract_fields",
    "model_available",
    "model_info",
    "spans_to_bio",
    "ENTITY_TYPES",
    "LABELS",
    "LABEL2ID",
    "ID2LABEL",
    "BASE_MODEL",
    "MODEL_DIR",
]
