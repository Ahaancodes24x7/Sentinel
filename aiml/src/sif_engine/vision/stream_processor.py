"""Continuous frame-processing pipeline for Live Safety Vision.

Owns the parts that make this "video", not "one classifier call":
  - the single lazily-loaded YOLO model, shared by every camera session
  - per-camera session state (active flag, rolling counts, dedupe cooldowns)
  - an optional background thread for a directly-opened source (RTSP or a
    server-local file), bounded so it cannot grow memory without limit and
    stoppable on demand

The browser-driven paths (webcam capture, an uploaded/local demo MP4 played
in the page) do NOT use the background thread - the frontend calls
POST /vision/analyze-frame on its own throttled timer, and `process_frame()`
below is the single entry point both paths go through, so detection + rule
logic is never duplicated between them.

This module has no database dependency by design (matching the rest of the
aiml package). Durable persistence of generated events is the backend's job:
`VisionSessionManager.set_event_sink()` lets backend/main.py register a
callback that writes new events to the database, without this module having
to import backend code.
"""
from __future__ import annotations

import base64
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

import cv2
import numpy as np

from . import camera_registry, hazard_rules
from .detector import YoloDetector
from .schemas import FrameAnalysis, SafetyEvent

# Server-side guard against a runaway/bursty caller: ~2.8 fps ceiling per
# camera regardless of what the frontend's own timer does.
MIN_FRAME_INTERVAL_SECONDS = 0.35

EventSink = Callable[[list[dict]], None]


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CameraSession:
    camera_id: str
    site_id: str
    active: bool = False
    source_type: Optional[str] = None
    people_count: int = 0
    vehicle_count: int = 0
    last_frame_at: Optional[datetime] = None
    last_processed_at: float = 0.0
    cooldowns: dict[str, float] = field(default_factory=dict)
    rtsp_worker: Optional["_BackgroundCaptureWorker"] = None


class VisionSessionManager:
    """Process-wide holder of all camera sessions and the shared detector."""

    def __init__(self):
        self._sessions: dict[str, CameraSession] = {}
        self._lock = threading.Lock()
        self._detector: Optional[YoloDetector] = None
        self._event_sink: Optional[EventSink] = None

    def set_event_sink(self, sink: Optional[EventSink]) -> None:
        """Register a callback invoked with every batch of newly created events.

        Used by the backend to persist events to the database. Both the HTTP
        (`analyze_frame`) and background-worker paths go through this, so
        events are durable regardless of which source drove the frame.
        """
        self._event_sink = sink

    def _get_detector(self) -> YoloDetector:
        if self._detector is None:
            self._detector = YoloDetector.get_instance()
        return self._detector

    def _get_or_create(self, camera_id: str, site_id: str) -> CameraSession:
        with self._lock:
            session = self._sessions.get(camera_id)
            if session is None:
                session = CameraSession(camera_id=camera_id, site_id=site_id)
                self._sessions[camera_id] = session
            else:
                session.site_id = site_id
            return session

    def start(
        self,
        camera_id: str,
        site_id: str,
        source_type: str,
        rtsp_url: Optional[str] = None,
    ) -> CameraSession:
        self.stop(camera_id)  # clean restart
        session = self._get_or_create(camera_id, site_id)
        session.active = True
        session.source_type = source_type
        session.people_count = 0
        session.vehicle_count = 0
        session.cooldowns = {}

        if source_type == "rtsp":
            if not rtsp_url:
                raise ValueError("rtsp_url is required when source_type='rtsp'")
            worker = _BackgroundCaptureWorker(self, camera_id, site_id, rtsp_url)
            session.rtsp_worker = worker
            worker.start()
        return session

    def stop(self, camera_id: str) -> Optional[CameraSession]:
        session = self._sessions.get(camera_id)
        if session is None:
            return None
        session.active = False
        if session.rtsp_worker:
            session.rtsp_worker.stop()
            session.rtsp_worker = None
        return session

    def mark_worker_dead(self, camera_id: str, worker: "_BackgroundCaptureWorker") -> None:
        """Called by a background worker thread when its capture loop ends on
        its own (source never opened, or a read failed) rather than via an
        explicit stop() - so `status()` stops reporting a session as active
        once nothing is actually processing frames for it. Guarded by
        identity so a worker that already lost a start/stop race can't clear
        a newer session's state."""
        with self._lock:
            session = self._sessions.get(camera_id)
            if session is not None and session.rtsp_worker is worker:
                session.active = False
                session.rtsp_worker = None

    def status(self, camera_id: str) -> dict:
        detector = self._get_detector()
        session = self._sessions.get(camera_id)
        base = {
            "camera_id": camera_id,
            "model_name": detector.model_name,
            "device": detector.device,
            "model_ready": detector.is_ready,
            "model_error": detector.load_error,
        }
        if session is None:
            base.update({
                "site_id": None,
                "active": False,
                "source_type": None,
                "people_count": 0,
                "vehicle_count": 0,
                "last_frame_at": None,
            })
            return base
        base.update({
            "site_id": session.site_id,
            "active": session.active,
            "source_type": session.source_type,
            "people_count": session.people_count,
            "vehicle_count": session.vehicle_count,
            "last_frame_at": session.last_frame_at,
        })
        return base

    def process_frame(
        self,
        camera_id: str,
        site_id: str,
        frame_bgr: np.ndarray,
        enforce_min_interval: bool = True,
    ) -> dict:
        """Run detection + hazard rules on one frame and update session state.

        `enforce_min_interval=False` lets a background worker (already
        throttled by its own capture loop) skip the extra guard meant for
        bursty HTTP callers.
        """
        session = self._get_or_create(camera_id, site_id)
        now_mono = time.monotonic()
        if enforce_min_interval and (now_mono - session.last_processed_at) < MIN_FRAME_INTERVAL_SECONDS:
            return {"skipped": True}
        session.last_processed_at = now_mono
        session.last_frame_at = _now()

        detector = self._get_detector()
        detections = detector.detect(frame_bgr)

        session.people_count = sum(1 for d in detections if d.class_name == "person")
        session.vehicle_count = sum(1 for d in detections if d.class_name in hazard_rules.VEHICLE_CLASSES)

        camera = camera_registry.get_camera(camera_id) or {
            "camera_id": camera_id,
            "camera_name": camera_id,
            "site_id": site_id,
            "rois": [],
        }
        drafts = hazard_rules.evaluate(detections, camera)

        new_events: list[SafetyEvent] = []
        now_ts = _now()
        now_epoch = time.monotonic()
        for draft in drafts:
            last_fired = session.cooldowns.get(draft.dedupe_key, 0.0)
            if now_epoch - last_fired < hazard_rules.EVENT_COOLDOWN_SECONDS:
                continue
            session.cooldowns[draft.dedupe_key] = now_epoch
            new_events.append(SafetyEvent(
                event_id=f"vis_{uuid.uuid4().hex[:10]}",
                timestamp=now_ts,
                site_id=site_id,
                camera_id=camera_id,
                camera_name=camera.get("camera_name", camera_id),
                event_type=draft.event_type,
                severity=draft.severity,
                confidence=draft.confidence,
                objects=[o.to_dict() for o in draft.objects],
                evidence=draft.evidence,
                roi=draft.roi,
                observed=draft.observed,
                inference=draft.inference,
                sif_relevance=draft.sif_relevance,
                lsr_tag=draft.lsr_tag,
            ))

        analysis = FrameAnalysis(
            camera_id=camera_id,
            site_id=site_id,
            frame_ts=now_ts,
            people_count=session.people_count,
            vehicle_count=session.vehicle_count,
            detections=[d.to_dict() for d in detections],
            new_events=new_events,
            model_name=detector.model_name,
            device=detector.device,
        )
        result = analysis.to_dict()

        if new_events and self._event_sink:
            try:
                self._event_sink(result["new_events"])
            except Exception:
                # Persistence failures must not break live inference - the
                # frontend still gets its detections/overlay this frame.
                pass

        return result

    @staticmethod
    def decode_base64_frame(image_base64: str) -> np.ndarray:
        if image_base64.strip().startswith("data:") and "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]
        raw = base64.b64decode(image_base64)
        arr = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Could not decode frame image data")
        return frame


class _BackgroundCaptureWorker(threading.Thread):
    """Best-effort background reader for an RTSP/IP-camera or local file source.

    Optional path: the demo does not depend on this working, since the
    frontend-driven webcam/upload path is the primary and reliable one. This
    holds at most the current frame (never a growing queue) and stops
    cleanly on `.stop()`.
    """

    def __init__(
        self,
        manager: VisionSessionManager,
        camera_id: str,
        site_id: str,
        source: str,
        target_fps: float = 2.0,
    ):
        super().__init__(daemon=True)
        self._manager = manager
        self._camera_id = camera_id
        self._site_id = site_id
        self._source = source
        self._interval = 1.0 / max(target_fps, 0.1)
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        cap = cv2.VideoCapture(self._source)
        try:
            if not cap.isOpened():
                self._mark_dead()
                return
            while not self._stop_event.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    self._mark_dead()
                    break
                self._manager.process_frame(
                    self._camera_id, self._site_id, frame, enforce_min_interval=False
                )
                time.sleep(self._interval)
        finally:
            cap.release()

    def _mark_dead(self) -> None:
        """The capture loop is ending on its own (source never opened, or
        read failed) rather than via an explicit `.stop()` - without this the
        session would keep reporting `active: true` forever even though no
        frames are being processed anymore, which would mislead the console.
        """
        self._manager.mark_worker_dead(self._camera_id, self)


_manager: Optional[VisionSessionManager] = None
_manager_lock = threading.Lock()


def get_manager() -> VisionSessionManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = VisionSessionManager()
        return _manager
