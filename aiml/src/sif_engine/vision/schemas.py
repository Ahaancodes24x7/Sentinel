"""Structured data contracts for CCTV hazard monitoring.

Plain stdlib dataclasses, not Pydantic - this keeps the aiml package's
existing, lighter dependency footprint (pandas / numpy / scikit-learn /
PyYAML) unchanged. Pydantic validation of these objects happens at the
FastAPI boundary in backend/schemas.py, which converts the dicts produced
here 1:1 into its own Vision* response models.

Every SafetyEvent keeps three things distinct, per the SIH brief:
  - `evidence` / `objects`  - the raw detector output the event is based on
  - `observed`              - what was literally seen
  - `inference`             - the safety interpretation a human still confirms

`regions` carries the pixel areas a scene-level analyzer flagged (the flame,
the plume, the falling mass, the person on the ground). Detection boxes alone
cannot express those, and without them the console could name a fire but not
show the operator where in frame it is.

`auto_report_*` is filled in by the backend once the event has been filed as
a complaint through the SIF pipeline. It lives on the event rather than in a
side table so that any consumer of the event stream - the console, the API,
an export - can see the report and priority the camera raised without a
second lookup.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SafetyEvent:
    event_id: str
    timestamp: datetime
    site_id: str
    camera_id: str
    camera_name: str
    # fire_detected | smoke_detected | visibility_loss | person_fall |
    # person_down_immobile | struck_by_falling_object | falling_object |
    # crowd_dispersal | crowd_surge | restricted_zone_entry |
    # lifting_zone_entry | vehicle_person_proximity
    event_type: str
    severity: str  # critical | high | medium | low
    confidence: float
    objects: list[dict]
    evidence: str
    roi: Optional[str]
    observed: str
    inference: str
    sif_relevance: str
    lsr_tag: str
    hazard_class: str = "scene"
    regions: list[dict] = field(default_factory=list)
    status: str = "active"  # active | acknowledged
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

    # Filled in by the backend after the complaint has been filed.
    auto_report_id: Optional[str] = None
    auto_report_priority: Optional[str] = None
    auto_report_bucket: Optional[str] = None
    auto_report_sif: Optional[bool] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FrameAnalysis:
    camera_id: str
    site_id: str
    frame_ts: datetime
    people_count: int
    vehicle_count: int
    detections: list[dict]
    new_events: list[SafetyEvent] = field(default_factory=list)
    model_name: str = ""
    device: str = "cpu"
    # Continuous scene signals for this frame: fire / smoke / motion /
    # visibility indices plus the flagged regions. The console renders these
    # live so an operator can watch a hazard index climb BEFORE it crosses a
    # threshold, rather than only seeing the alarm after the fact.
    signals: dict = field(default_factory=dict)
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "camera_id": self.camera_id,
            "site_id": self.site_id,
            "frame_ts": self.frame_ts,
            "people_count": self.people_count,
            "vehicle_count": self.vehicle_count,
            "detections": self.detections,
            "new_events": [e.to_dict() for e in self.new_events],
            "model_name": self.model_name,
            "device": self.device,
            "signals": self.signals,
            "latency_ms": self.latency_ms,
        }
