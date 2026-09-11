"""CCTV hazard monitoring for Sentinel.

Separate from the Stage 1/2 NLP pipeline on purpose: this package reasons over
video frames, not report text. Nothing here is imported by, or changes the
behaviour of, sif_engine.extraction / reasoning / pipeline.

    detector.py          - loads a YOLO model once, returns structured detections
    scene_analysis.py    - fire, smoke, visibility, fall and falling-mass
                           analyzers; the half of the problem a COCO detector
                           cannot see
    camera_registry.py   - site / camera / safety-zone configuration
    hazard_rules.py      - turns detections + scene signals into event drafts
    incident_report.py   - drafts the automatic complaint an event files
    stream_processor.py  - per-camera session state, frame loop, event sink
    schemas.py           - plain dataclasses for the safety-event contract

The flow for one frame is:

    frame -> YoloDetector.detect        -> boxes
          -> SceneAnalyzer.analyze      -> fire/smoke/fall/descent signals
          -> hazard_rules.evaluate      -> EventDraft list, severity ordered
          -> stream_processor           -> dedupe, SafetyEvent, event sink
          -> (backend) incident_report  -> complaint text -> SIF pipeline
                                        -> priority -> reports queue
"""

from .detector import DetectedObject, YoloDetector
from .scene_analysis import SceneAnalyzer, SceneSignals
from .stream_processor import get_manager

__all__ = [
    "DetectedObject",
    "YoloDetector",
    "SceneAnalyzer",
    "SceneSignals",
    "get_manager",
]
