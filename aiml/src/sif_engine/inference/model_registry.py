"""
Model Registry for SIF and LSR Inference.

Manages model resolution, lazy loading, and switching between:
  - 'baseline2' (Default production model: TF-IDF + Logistic Regression)
  - 'mlp' (Benchmark model: MLP neural network)
"""

import os
from pathlib import Path
from typing import Any, Optional

from sif_engine.inference.baseline2 import Baseline2Model
from sif_engine.inference.mlp import MLPModel

DEFAULT_SIF_MODEL = "baseline2"


class ModelRegistry:
    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = models_dir
        self._models: dict[str, Any] = {}

    def get_configured_model_name(self) -> str:
        env_val = os.environ.get("SENTINEL_SIF_MODEL", "").strip().lower()
        if env_val in ("baseline2", "mlp"):
            return env_val
        return DEFAULT_SIF_MODEL

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
            else:
                raise ValueError(f"Unknown model name: '{model_name}'. Available: 'baseline2', 'mlp'")
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

    def get_metadata(self) -> dict[str, Any]:
        active_name = self.get_configured_model_name()
        active_inst = self.get_model(active_name)
        return {
            "active_sif_model": active_name,
            "model_version": getattr(active_inst, "MODEL_VERSION", "unknown"),
            "default_sif_model": DEFAULT_SIF_MODEL,
            "mlp_available": self.is_mlp_available(),
            "available_models": ["baseline2", "mlp"],
        }


# Global singleton registry
_registry = ModelRegistry()


def get_active_model():
    return _registry.get_active_model()


def get_model(name: Optional[str] = None):
    return _registry.get_model(name)


def get_model_metadata() -> dict[str, Any]:
    return _registry.get_metadata()
