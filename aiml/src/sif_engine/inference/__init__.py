"""
Inference interfaces for SIF Precursor Detection.
"""

from sif_engine.inference.baseline2 import Baseline2Model
from sif_engine.inference.mlp import MLPModel
from sif_engine.inference.model_registry import (
    DEFAULT_SIF_MODEL,
    ModelRegistry,
    get_active_model,
    get_model,
    get_model_metadata,
)

__all__ = [
    "Baseline2Model",
    "MLPModel",
    "ModelRegistry",
    "DEFAULT_SIF_MODEL",
    "get_active_model",
    "get_model",
    "get_model_metadata",
]
