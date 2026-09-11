"""YOLO-based object detector for mine / field CCTV hazard monitoring.

Loads an Ultralytics YOLO model exactly once (module-level singleton) and
reuses it for every frame - the requirement is "load once, infer many", not
"construct a model per request". Falls back to CPU automatically when no CUDA
device is available, and never raises if the vision dependencies or weights
are missing: callers get `is_ready == False` and a human-readable
`load_error` instead of a crashed backend, so the rest of Sentinel keeps
working even if this feature cannot start.

Three things here exist because of failures seen in practice:

* **One inference at a time.** FastAPI runs sync endpoints in a thread pool,
  so several frames can reach `detect()` concurrently the moment the frontend
  timer outruns inference. An Ultralytics model is not safe to call
  re-entrantly - it mutates internal state per predict - and doing so
  produces sporadic tensor-shape and device errors that look like random
  corruption. A single lock serialises inference; the cost is bounded because
  the caller is already frame-rate limited upstream.
* **Warm up on load.** The very first `predict()` pays for lazy graph
  construction and is ~30x slower than steady state. Paying that during model
  load, not on the first live frame, is what stops a camera session from
  appearing to hang the moment it starts.
* **Keep the classes that matter, not only person/vehicle.** A mine scene
  contains plant, tools and loose material that a COCO model can partially
  name, and a mass falling through frame needs a label even when the model
  has no idea what it is. Detections are therefore split into
  `RELEVANT_CLASSES` (drive the rules) and everything else (dropped), with
  the relevant set widened to the objects a dropped-object rule can use.
"""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# People and anything that can move, be driven, be lifted or be dropped. The
# underlying model is COCO-pretrained and knows 80 classes; the rest (food,
# furniture, animals) carry no safety meaning on a mine site and are dropped
# at the source rather than leaking noise into the UI.
PERSON_CLASS = "person"
VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle", "train", "boat", "airplane"}
# Objects a dropped-object / struck-by rule can meaningfully name when one of
# them descends through the frame. Everything genuinely unknown is still
# caught by the motion-blob path in scene_analysis.py, which needs no class.
DROPPABLE_CLASSES = {
    "backpack", "umbrella", "handbag", "suitcase", "sports ball", "bottle",
    "cup", "chair", "bench", "tv", "laptop", "keyboard", "cell phone",
    "book", "clock", "vase", "scissors", "hair drier", "toothbrush",
    "skateboard", "snowboard", "surfboard", "tennis racket", "baseball bat",
    "fire hydrant", "stop sign", "parking meter", "potted plant",
}
RELEVANT_CLASSES = {PERSON_CLASS} | VEHICLE_CLASSES | DROPPABLE_CLASSES

_MODEL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "models" / "vision"
_DEFAULT_WEIGHTS = "yolov8n.pt"
_DEFAULT_IMGSZ = int(os.getenv("SENTINEL_VISION_IMGSZ", "640"))

# Lower than a typical demo threshold on purpose. This system is specified to
# tolerate false alarms and not to tolerate misses, and a half-occluded worker
# in poor underground light routinely scores in the 0.25-0.35 band. Anything
# weaker than this is noise even by that standard.
_DEFAULT_CONF = float(os.getenv("SENTINEL_VISION_CONF", "0.25"))


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

    def __init__(self, weights: Optional[str] = None, conf_threshold: float = _DEFAULT_CONF):
        self.conf_threshold = conf_threshold
        self._model = None
        self._device = "cpu"
        self._load_error: Optional[str] = None
        self._infer_lock = threading.Lock()
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
        env = os.getenv("SENTINEL_VISION_WEIGHTS")
        if env and Path(env).is_file():
            return env
        local = _MODEL_DIR / _DEFAULT_WEIGHTS
        if local.is_file():
            return str(local)
        # A previous run of Ultralytics caches the weights in the working
        # directory; prefer that over triggering another download.
        cwd_copy = Path.cwd() / _DEFAULT_WEIGHTS
        if cwd_copy.is_file():
            return str(cwd_copy)
        # Not cached anywhere - Ultralytics downloads and caches the
        # pretrained weights on first use.
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
            self._load_error = f"Failed to load YOLO weights {self._weights_path!r}: {exc}"
            self._model = None
            return
        self._warmup()

    def _warmup(self) -> None:
        """Run one throwaway inference so the first live frame is not the one
        that pays for lazy graph construction."""
        try:
            blank = np.zeros((_DEFAULT_IMGSZ // 2, _DEFAULT_IMGSZ, 3), dtype=np.uint8)
            self._model.predict(
                blank, imgsz=_DEFAULT_IMGSZ, device=self._device, verbose=False
            )
        except Exception:
            logger.warning("YOLO warmup inference failed; continuing", exc_info=True)

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

        Returns an empty list (never raises) if the model failed to load - the
        rule layer and the API both treat "no detections" and "model
        unavailable" the same way, with the status endpoint carrying the real
        reason.
        """
        if self._model is None or frame_bgr is None or frame_bgr.size == 0:
            return []
        if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
            return []
        h, w = frame_bgr.shape[:2]
        if h == 0 or w == 0:
            return []

        try:
            # Serialised: see the module docstring. imgsz lets Ultralytics do
            # the resize internally rather than the caller pre-resizing with
            # OpenCV, which is one fewer array copy per frame.
            with self._infer_lock:
                results = self._model.predict(
                    frame_bgr,
                    conf=self.conf_threshold,
                    imgsz=_DEFAULT_IMGSZ,
                    device=self._device,
                    verbose=False,
                )
        except Exception:
            # One malformed or corrupt frame must not crash a continuous video
            # loop or 500 the analyze-frame endpoint - log it and treat this
            # frame as "no detections", matching the never-raises contract
            # documented above.
            logger.exception("YOLO inference failed on one frame; skipping it")
            return []

        detections: list[DetectedObject] = []
        for result in results:
            names = result.names
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                try:
                    cls_id = int(box.cls[0])
                    class_name = (
                        names.get(cls_id, str(cls_id)) if isinstance(names, dict) else names[cls_id]
                    )
                    if class_name not in RELEVANT_CLASSES:
                        continue
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
                except Exception:
                    continue
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
            "conf_threshold": self.conf_threshold,
            "imgsz": _DEFAULT_IMGSZ,
        }
