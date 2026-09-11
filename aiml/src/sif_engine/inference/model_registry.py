"""
Model Registry for SIF and LSR Inference.

Manages model resolution, lazy loading, and switching between:
  - 'baseline2'   (TF-IDF + Logistic Regression — always available, no download)
  - 'mlp'         (Benchmark model: MLP neural network)
  - 'transformer' (Fine-tuned DistilBERT — the strongest classifier measured in
                    this project; see inference/transformer.py for the metrics)

Resolution order when no explicit name is given: SENTINEL_SIF_MODEL if set,
else the transformer if its checkpoint is actually present on disk, else
'baseline2'. A fresh clone without the (gitignored, ~256 MB) transformer
checkpoint keeps working on baseline2 with no code change required; an
environment that has trained/downloaded the checkpoint gets the better model
automatically rather than needing an env var nobody would think to set.
"""

import os
from pathlib import Path
from typing import Any, Optional

from sif_engine.inference.baseline2 import Baseline2Model
from sif_engine.inference.mlp import MLPModel
from sif_engine.inference.transformer import TransformerModel

DEFAULT_SIF_MODEL = "baseline2"
AVAILABLE_MODELS = ("baseline2", "mlp", "transformer")


class ModelRegistry:
    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = models_dir
        self._models: dict[str, Any] = {}

    def get_configured_model_name(self) -> str:
        env_val = os.environ.get("SENTINEL_SIF_MODEL", "").strip().lower()
        if env_val in AVAILABLE_MODELS:
            return env_val
        if env_val:
            # Explicitly misconfigured is a louder failure mode than silently
            # ignoring it would be, but this registry is queried on every
            # request, so it degrades to the safe default rather than raising.
            return DEFAULT_SIF_MODEL
        return "transformer" if self.is_transformer_available() else DEFAULT_SIF_MODEL

    def get_model(self, name: Optional[str] = None) -> Any:
        model_name = (name or self.get_configured_model_name()).lower()
        if model_name not in self._models:
            if model_name == "baseline2":
                inst = Baseline2Model(models_dir=self.models_dir)
                inst.load()
                self._models[model_name] = inst
            elif model_name == "mlp":
                inst = MLPModel(models_dir=self.models_dir)
                inst.load()
                self._models[model_name] = inst
            elif model_name == "transformer":
                inst = TransformerModel(models_dir=self.models_dir)
                inst.load()
                self._models[model_name] = inst
            else:
                raise ValueError(
                    f"Unknown model name: '{model_name}'. Available: {list(AVAILABLE_MODELS)}"
                )
        return self._models[model_name]

    def get_active_model(self) -> Any:
        return self.get_model(self.get_configured_model_name())

    def is_mlp_available(self) -> bool:
        try:
            mlp_inst = MLPModel(models_dir=self.models_dir)
            mlp_inst.load()
            return True
        except Exception:
            return False

    def is_transformer_available(self) -> bool:
        try:
            tf_inst = TransformerModel(models_dir=self.models_dir)
            return tf_inst._checkpoint_dir.is_dir()
        except Exception:
            return False

    def get_metadata(self) -> dict[str, Any]:
        active_name = self.get_configured_model_name()
        try:
            active_inst = self.get_model(active_name)
            model_version = getattr(active_inst, "MODEL_VERSION", "unknown")
            load_error = None
        except Exception as exc:
            # A model that fails to load (missing checkpoint, missing optional
            # dependency) must not 500 the health endpoint — report the gap
            # instead, the same "never crash, say why" contract the rest of
            # the pipeline follows for optional components.
            model_version = "unavailable"
            load_error = str(exc)
        return {
            "active_sif_model": active_name,
            "model_version": model_version,
            "default_sif_model": DEFAULT_SIF_MODEL,
            "mlp_available": self.is_mlp_available(),
            "transformer_available": self.is_transformer_available(),
            "available_models": list(AVAILABLE_MODELS),
            "load_error": load_error,
        }


# Global singleton registry
_registry = ModelRegistry()


def get_active_model():
    return _registry.get_active_model()


def get_model(name: Optional[str] = None):
    return _registry.get_model(name)


def get_model_metadata() -> dict[str, Any]:
    return _registry.get_metadata()
