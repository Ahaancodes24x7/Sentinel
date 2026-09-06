"""
Baseline 2 SIF & LSR Inference Module.

Loads the production-default TF-IDF + Calibrated Logistic Regression models
for SIF potential classification and Life-Saving Rule (LSR) tagging.
"""

from pathlib import Path
import pickle
from typing import Any, Optional

from sif_engine.preprocessing import preprocess_report


class Baseline2Model:
    MODEL_VERSION = "baseline2-v0.3"

    def __init__(self, models_dir: Optional[Path] = None):
        if models_dir is None:
            # Resolves Sentinel/aiml/models
            self.models_dir = Path(__file__).resolve().parent.parent.parent.parent / "models"
        else:
            self.models_dir = Path(models_dir)

        self._sif_artifact: Optional[dict[str, Any]] = None
        self._lsr_artifact: Optional[dict[str, Any]] = None

    def _resolve_path(self, subfolder_name: str, fallback_name: str) -> Path:
        primary = self.models_dir / "baseline2" / fallback_name
        if primary.is_file():
            return primary
        fallback = self.models_dir / fallback_name
        if fallback.is_file():
            return fallback
        raise FileNotFoundError(f"Baseline 2 artifact not found at {primary} or {fallback}")

    def load(self) -> None:
        if self._sif_artifact is None:
            sif_path = self._resolve_path("baseline2", "sif_classifier_baseline2.pkl")
            with open(sif_path, "rb") as f:
                self._sif_artifact = pickle.load(f)

        if self._lsr_artifact is None:
            lsr_path = self._resolve_path("baseline2", "lsr_classifier_baseline2b.pkl")
            with open(lsr_path, "rb") as f:
                self._lsr_artifact = pickle.load(f)

    @property
    def is_loaded(self) -> bool:
        return self._sif_artifact is not None and self._lsr_artifact is not None

    def predict(self, text: str) -> dict[str, Any]:
        self.load()
        assert self._sif_artifact is not None
        assert self._lsr_artifact is not None

        clean_text = preprocess_report(text)

        # SIF inference
        sif_vec = self._sif_artifact["vectorizer"]
        sif_clf = self._sif_artifact["model"]

        X_sif = sif_vec.transform([clean_text])
        prob_array = sif_clf.predict_proba(X_sif)[0]
        sif_prob = float(prob_array[1])
        sif_pred = int(sif_clf.predict(X_sif)[0])
        sif_bool = bool(sif_pred == 1)

        # 4-bucket routing
        if sif_bool and sif_prob >= 0.75:
            bucket = "HIGH_CONF_SIF"
        elif sif_bool and sif_prob < 0.75:
            bucket = "LOW_CONF_REVIEW"
        elif not sif_bool and sif_prob <= 0.25:
            bucket = "HIGH_CONF_NON_SIF"
        else:
            bucket = "LOW_CONF_REVIEW"

        # Confidence is calibrated class probability
        confidence = round(sif_prob if sif_bool else (1.0 - sif_prob), 2)

        # LSR tagging
        lsr_vec = self._lsr_artifact["vectorizer"]
        lsr_clf = self._lsr_artifact["model"]
        X_lsr = lsr_vec.transform([clean_text])
        lsr_tag = str(lsr_clf.predict(X_lsr)[0])

        justification = (
            f"Flagged as {'SIF-potential' if sif_bool else 'non-SIF'} "
            f"with {round(sif_prob * 100, 1)}% probability ({bucket}). "
            f"Assigned Life-Saving Rule: {lsr_tag}."
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
        }
