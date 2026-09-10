"""YOLO-based object detector for Live Safety Vision.

Loads an Ultralytics YOLO model exactly once (module-level singleton) and
reuses it for every frame - the MVP requirement is "load once, infer many",
not "construct a model per request". Falls back to CPU automatically when no
CUDA device is available, and never raises if the vision dependencies or
weights are missing: callers get `is_ready == False` and a human-readable
`load_error` instead of a crashed backend, so the rest of Sentinel keeps
working even if this optional feature cannot start.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

# The underlying model is a generic COCO-pretrained YOLO - it recognizes far
# more classes than this. Only people and vehicles are relevant to the
# hazard-rule layer, so everything else is discarded at the source rather
# than leaking irrelevant boxes into the UI.
RELEVANT_CLASSES = {"person", "car", "truck", "bus", "motorcycle", "bicycle"}

_MODEL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "models" / "vision"
_DEFAULT_WEIGHTS = "yolov8n.pt"
_DEFAULT_IMGSZ = 640


@dataclass
class DetectedObject:
    class_name: str
    confidence: float
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2) normalized 0..1

    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0

    def to_dict(self) -> dict:
        return {
            "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox": [round(v, 4) for v in self.bbox],
        }


class YoloDetector:
    """Thread-safe singleton wrapper around one Ultralytics YOLO model."""

    _instance: Optional["YoloDetector"] = None
    _instance_lock = threading.Lock()

    def __init__(self, weights: Optional[str] = None, conf_threshold: float = 0.35):
        self.conf_threshold = conf_threshold
        self._model = None
        self._device = "cpu"
        self._load_error: Optional[str] = None
        self._weights_path = self._resolve_weights(weights)
        self._load()

    @classmethod
    def get_instance(cls) -> "YoloDetector":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    @staticmethod
    def _resolve_weights(weights: Optional[str]) -> str:
        if weights:
            return weights
        local = _MODEL_DIR / _DEFAULT_WEIGHTS
        if local.is_file():
            return str(local)
        # Not cached locally under aiml/models/vision - Ultralytics will
        # download and cache the pretrained weights on first use.
        return _DEFAULT_WEIGHTS

    def _load(self) -> None:
        try:
            import torch
            from ultralytics import YOLO
        except Exception as exc:  # pragma: no cover - optional dependency missing
            self._load_error = (
                "Vision dependencies unavailable "
                f"(pip install ultralytics opencv-python torch): {exc}"
            )
            return
        try:
            self._model = YOLO(self._weights_path)
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception as exc:  # pragma: no cover - depends on network/weights
            self._load_error = f"Failed to load YOLO weights '{self._weights_path}': {exc}"
            self._model = None

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    @property
    def device(self) -> str:
        return self._device

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    @property
    def model_name(self) -> str:
        return Path(self._weights_path).stem

    def detect(self, frame_bgr: np.ndarray) -> list[DetectedObject]:
        """Run inference on one BGR frame (HxWx3, uint8) and return detections.

        Returns an empty list (never raises) if the model failed to load -
        the hazard-rule layer and the API both treat "no detections" and
        "model unavailable" the same way, with the status endpoint carrying
        the actual reason.
        """
        if self._model is None or frame_bgr is None or frame_bgr.size == 0:
            return []
        h, w = frame_bgr.shape[:2]
        if h == 0 or w == 0:
            return []

        # imgsz lets Ultralytics handle the resize internally rather than the
        # caller pre-resizing with OpenCV - one fewer array copy per frame.
        results = self._model.predict(
            frame_bgr,
            conf=self.conf_threshold,
            imgsz=_DEFAULT_IMGSZ,
            device=self._device,
            verbose=False,
        )

        detections: list[DetectedObject] = []
        for result in results:
            names = result.names
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0])
                class_name = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else names[cls_id]
                if class_name not in RELEVANT_CLASSES:
                    continue
                conf = float(box.conf[0])
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
                detections.append(
                    DetectedObject(
                        class_name=class_name,
                        confidence=conf,
                        bbox=(
                            max(0.0, min(1.0, x1 / w)),
                            max(0.0, min(1.0, y1 / h)),
                            max(0.0, min(1.0, x2 / w)),
                            max(0.0, min(1.0, y2 / h)),
                        ),
                    )
                )
        return detections

    def status(self) -> dict:
        return {
            "model_name": self.model_name,
            "device": self._device,
            "ready": self.is_ready,
            "error": self._load_error,
        }
