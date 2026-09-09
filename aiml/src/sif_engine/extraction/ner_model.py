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
    """Deterministic extraction when no transformer artefact is available.

    Reads the actual shape `extract_evidence` returns. The previous version
    looked for an "evidence_spans" key that function has never produced — that
    key is assembled downstream in pipeline.py — so this silently returned zero
    spans on every machine without the fine-tuned model, which is most of them.
    A fallback that quietly extracts nothing is worse than no fallback: the
    caller cannot tell "no entities here" from "I did not run".
    """
    try:
        from sif_engine.extraction.evidence_extractor import extract_evidence
    except Exception:
        return {"spans": [], "source": "unavailable"}

    try:
        ev = extract_evidence(text)
    except Exception:
        return {"spans": [], "source": "unavailable"}

    spans: list[dict[str, Any]] = []

    def add(label: str, span_text: Any, offsets: Any, confidence: float) -> None:
        if not span_text or not offsets:
            return
        try:
            start, end = int(offsets[0]), int(offsets[1])
        except (TypeError, IndexError, ValueError):
            return
        if end <= start or end > len(text):
            return
        # Only emit a span whose offsets really do slice back to its own text,
        # so the highlighting contract holds for the fallback exactly as it
        # does for the transformer.
        if text[start:end] != span_text:
            return
        spans.append({
            "label": label,
            "text": span_text,
            "span": [start, end],
            "confidence": round(float(confidence), 4),
        })

    activity = ev.get("activity") or {}
    add("ACTIVITY", activity.get("text"), activity.get("span"),
        activity.get("confidence", 0.6))

    location = ev.get("location") or {}
    add("LOCATION", location.get("text"), location.get("span"),
        location.get("confidence", 0.9))

    exposure = ev.get("exposure") or {}
    for item in (exposure.get("evidence") or []):
        add("EXPOSURE", getattr(item, "text", None), getattr(item, "span", None),
            exposure.get("confidence", 0.7))

    barrier = ev.get("barrier")
    for item in (getattr(barrier, "evidence", None) or []):
        add("BARRIER", getattr(item, "text", None), getattr(item, "span", None),
            getattr(barrier, "confidence", 0.7))

    hazard = ev.get("hazard") or {}
    for _category, items in (hazard.get("matches") or {}).items():
        for item in items or []:
            add("HAZARD", getattr(item, "text", None), getattr(item, "span", None), 0.75)

    # Drop shorter spans nested inside a longer one of the same label - the cue
    # lists deliberately overlap ("within the immediate" inside "within the
    # immediate hazard zone") and only the widest match is useful to highlight.
    spans.sort(key=lambda s: (s["span"][0], -(s["span"][1] - s["span"][0])))
    kept: list[dict[str, Any]] = []
    for span in spans:
        if any(
            other["label"] == span["label"]
            and other["span"][0] <= span["span"][0]
            and other["span"][1] >= span["span"][1]
            for other in kept
        ):
            continue
        kept.append(span)

    kept.sort(key=lambda s: s["span"][0])
    return {"spans": kept, "source": "rule_fallback"}


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
