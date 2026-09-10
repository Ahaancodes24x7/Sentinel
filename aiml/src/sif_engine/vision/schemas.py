"""Structured data contracts for Live Safety Vision.

Plain stdlib dataclasses, not Pydantic - this keeps the aiml package's
existing, lighter dependency footprint (pandas / numpy / scikit-learn /
PyYAML) unchanged. Pydantic validation of these objects happens at the
FastAPI boundary in backend/schemas.py, which converts the dicts produced
here 1:1 into its own Vision* response models.

Every SafetyEvent keeps three things distinct, per the SIH brief:
  - `evidence` / `objects`  — the raw detector output the event is based on
  - `observed`              — what was literally seen (object + zone/proximity)
  - `inference`             — the safety interpretation a human still confirms
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
    event_type: str  # restricted_zone_entry | lifting_zone_entry | vehicle_person_proximity
    severity: str  # high | medium | low
    confidence: float
    objects: list[dict]
    evidence: str
    roi: Optional[str]
    observed: str
    inference: str
    sif_relevance: str
    lsr_tag: str
    status: str = "active"  # active | acknowledged
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

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
        }
