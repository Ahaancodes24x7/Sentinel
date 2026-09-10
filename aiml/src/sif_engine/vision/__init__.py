"""Live Safety Vision — computer-vision safety monitoring for Sentinel.

Separate from the Stage 1/2 NLP pipeline on purpose: this package reasons
over video frames (YOLO object detection + a configurable ROI hazard-rule
layer), not report text. Nothing here is imported by, or changes the
behaviour of, sif_engine.extraction / reasoning / pipeline.

    detector.py         — loads a YOLO model once, returns structured detections
    camera_registry.py  — demo site/camera/ROI configuration
    hazard_rules.py      — turns detections + ROIs into safety-event drafts
    stream_processor.py  — per-camera session state, frame loop, event sink
    schemas.py            — plain dataclasses for the safety-event contract
"""

from .detector import DetectedObject, YoloDetector
from .stream_processor import get_manager

__all__ = ["DetectedObject", "YoloDetector", "get_manager"]
