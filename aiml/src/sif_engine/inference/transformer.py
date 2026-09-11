"""
Fine-tuned DistilBERT SIF Inference Module.

Loads the fine-tuned transformer classifier from
``scripts/train_transformer_part2_finetune.py`` — DistilBERT fine-tuned
end-to-end as a binary sequence classifier, not a frozen-embedding head. It is
the strongest single classifier benchmarked in this project (precision 0.963,
recall 0.962, ROC-AUC 0.970 on the held-out synthetic test split — see
``reports/transformer_part2_distilbert_finetuned_metrics.json``), which is why
it is wired in here as a third selectable backend alongside 'baseline2' and
'mlp', through the same ModelRegistry those already use.

The fine-tuned checkpoint was trained only for the binary sif_potential task
(no LSR head), so LSR tagging here is borrowed from the existing Baseline 2
TF-IDF+LogReg LSR tagger rather than left unset — the same "strongest
classifier for one axis, existing tagger for the other" composition
``scripts/train_transformer_part3_hybrid.py`` uses for its hybrid variant.
"""

from __future__ import annotations

import pickle
import threading
from pathlib import Path
from typing import Any, Optional

from sif_engine.preprocessing import preprocess_report

MAX_LENGTH = 128


class TransformerModel:
    MODEL_VERSION = "distilbert-finetuned-v2.0"
    _CHECKPOINT_PARTS = ("transformers", "distilbert_finetuned", "final")

    def __init__(self, models_dir: Optional[Path] = None):
        if models_dir is None:
            # Resolves Sentinel/aiml/models
            self.models_dir = Path(__file__).resolve().parent.parent.parent.parent / "models"
        else:
            self.models_dir = Path(models_dir)

        self._tokenizer = None
        self._model = None
        self._device = "cpu"
        self._lsr_artifact: Optional[dict[str, Any]] = None
        self._load_lock = threading.Lock()

    @property
    def _checkpoint_dir(self) -> Path:
        return self.models_dir.joinpath(*self._CHECKPOINT_PARTS)

    def load(self) -> None:
        if self._model is not None:
            return
        with self._load_lock:
            if self._model is not None:
                return

            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            ckpt = self._checkpoint_dir
            if not ckpt.is_dir():
                raise FileNotFoundError(
                    f"Fine-tuned transformer checkpoint not found at {ckpt}. Regenerate with:\n"
                    "    python scripts/train_transformer_part2_finetune.py"
                )

            tokenizer = AutoTokenizer.from_pretrained(str(ckpt))
            model = AutoModelForSequenceClassification.from_pretrained(str(ckpt))
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(device)
            model.eval()

            lsr_path = self.models_dir / "baseline2" / "lsr_classifier_baseline2b.pkl"
            if not lsr_path.is_file():
                lsr_path = self.models_dir / "lsr_classifier_baseline2b.pkl"
            lsr_artifact = None
            if lsr_path.is_file():
                with open(lsr_path, "rb") as f:
                    lsr_artifact = pickle.load(f)

            self._tokenizer = tokenizer
            self._model = model
            self._device = device
            self._lsr_artifact = lsr_artifact

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _predict_lsr(self, clean_text: str) -> str:
        if self._lsr_artifact is None:
            return "Work Authorisation"
        model = self._lsr_artifact["model"]
        vectorizer = self._lsr_artifact.get("vectorizer")
        features = vectorizer.transform([clean_text]) if vectorizer is not None else [clean_text]
        return str(model.predict(features)[0])

    def predict(self, text: str) -> dict[str, Any]:
        self.load()
        import torch

        assert self._model is not None and self._tokenizer is not None

        clean_text = preprocess_report(text)
        encoded = self._tokenizer(
            clean_text, truncation=True, max_length=MAX_LENGTH, return_tensors="pt"
        ).to(self._device)

        with torch.no_grad():
            logits = self._model(**encoded).logits
            probs = torch.softmax(logits, dim=-1)[0]
        sif_prob = float(probs[1].item())

        # Same operating logic as the other registry models (0.5 decision
        # boundary; 0.75/0.25 split the confident half of each side into its
        # own bucket) — kept identical across backends so switching models
        # via SENTINEL_SIF_MODEL changes which model answers, not what the
        # bucket boundaries mean.
        sif_bool = sif_prob >= 0.5
        if sif_bool and sif_prob >= 0.75:
            bucket = "HIGH_CONF_SIF"
        elif sif_bool:
            bucket = "LOW_CONF_REVIEW"
        elif sif_prob <= 0.25:
            bucket = "HIGH_CONF_NON_SIF"
        else:
            bucket = "LOW_CONF_REVIEW"

        confidence = round(sif_prob if sif_bool else (1.0 - sif_prob), 3)
        lsr_tag = self._predict_lsr(clean_text)

        justification = (
            f"Fine-tuned DistilBERT classifier scored {round(sif_prob * 100, 1)}% "
            f"SIF-potential probability ({bucket}). LSR tag from the TF-IDF+LogReg "
            f"tagger — the fine-tuned checkpoint was trained only for the binary "
            f"task and has no LSR head: {lsr_tag}."
        )

        return {
            "sif_potential": sif_bool,
            "confidence": confidence,
            "bucket": bucket,
            "lsr_tag": lsr_tag,
            "justification": justification,
            "model_version": self.MODEL_VERSION,
            "raw_probability": round(sif_prob, 4),
            "preprocessed_text": clean_text,
            "device": self._device,
        }
