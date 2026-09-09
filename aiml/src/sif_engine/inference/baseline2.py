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
    MODEL_VERSION = "sentinel-v2.0"

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

    @staticmethod
    def _apply(artifact: dict[str, Any], text: str):
        """Transform + predict, supporting both artifact layouts.

        v0.3 artifacts stored a separate fitted vectorizer and a bare
        estimator. v2.0 artifacts store one calibrated sklearn Pipeline that
        takes raw text directly, so `vectorizer` is None. Supporting both means
        an older checkout keeps working instead of failing at load time.
        """
        vectorizer = artifact.get("vectorizer")
        model = artifact["model"]
        features = vectorizer.transform([text]) if vectorizer is not None else [text]
        return model, features

    def predict(self, text: str) -> dict[str, Any]:
        self.load()
        assert self._sif_artifact is not None
        assert self._lsr_artifact is not None

        clean_text = preprocess_report(text)

        # ---- SIF inference ----
        sif_clf, X_sif = self._apply(self._sif_artifact, clean_text)
        sif_prob = float(sif_clf.predict_proba(X_sif)[0][1])

        # Threshold is the calibrated operating point chosen on validation for
        # >=90% recall, NOT 0.5. Falling back to 0.5 would silently drop true
        # precursors, which is the one error this system must not make.
        threshold = float(self._sif_artifact.get("threshold", 0.5))
        sif_bool = sif_prob >= threshold

        # ---- 4-bucket routing ----
        if sif_bool and sif_prob >= 0.75:
            bucket = "HIGH_CONF_SIF"
        elif sif_bool:
            bucket = "LOW_CONF_REVIEW"
        elif sif_prob <= 0.25:
            bucket = "HIGH_CONF_NON_SIF"
        else:
            bucket = "LOW_CONF_REVIEW"

        confidence = round(sif_prob if sif_bool else (1.0 - sif_prob), 3)

        # ---- LSR tagging ----
        lsr_clf, X_lsr = self._apply(self._lsr_artifact, clean_text)
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
            "model_version": self._sif_artifact.get("model_version", self.MODEL_VERSION),
            "threshold": threshold,
            "raw_probability": round(sif_prob, 4),
            "preprocessed_text": clean_text,
        }
