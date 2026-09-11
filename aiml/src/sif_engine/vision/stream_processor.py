"""Continuous frame-processing pipeline for CCTV hazard monitoring.

Owns the parts that make this "video", not "one classifier call":

  - the single lazily-loaded YOLO model, shared by every camera
  - a per-camera SceneAnalyzer holding the temporal state that fire flicker,
    smoke growth, fall posture and falling-mass tracking all depend on
  - per-camera session state (active flag, rolling counts, dedupe cooldowns)
  - an optional background thread for a directly-opened source (RTSP or a
    server-local file), bounded so it cannot grow memory without limit and
    stoppable on demand

The browser-driven paths (webcam capture, an uploaded video played in the
page) do NOT use the background thread - the frontend calls
POST /vision/analyze-frame on its own throttled timer, and `process_frame()`
below is the single entry point every path goes through, so detection, scene
analysis and rule logic are never duplicated between them.

Per-camera analyzer state is the reason `start()` resets rather than reuses a
session: temporal signals computed across a source switch (webcam frame
followed by a video frame) are meaningless, and a background model built from
one scene would mark the whole of the next scene as motion.

This module has no database dependency by design (matching the rest of the
aiml package). Durable persistence of generated events, and filing them as
complaints, is the backend's job: `VisionSessionManager.set_event_sink()`
lets backend/main.py register a callback that both writes events and runs the
auto-report pipeline, without this module importing backend code.
"""
from __future__ import annotations

import base64
import binascii
import logging
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
from .scene_analysis import SceneAnalyzer
from .schemas import FrameAnalysis, SafetyEvent

logger = logging.getLogger(__name__)

# Server-side guard against a runaway or bursty caller: ~5 fps ceiling per
# camera regardless of what the frontend timer does. Higher than a pure
# object detector would need, because the temporal analyzers (flicker, fall
# posture, descent speed) get materially better with frame rate and the whole
# per-frame cost is ~50 ms.
MIN_FRAME_INTERVAL_SECONDS = 0.20

# Frames whose largest side exceeds this are downscaled before anything runs.
# A 4K CCTV still costs several times more to decode and infer on with no
# detection benefit at the distances these cameras cover.
MAX_FRAME_WIDTH = 1280

EventSink = Callable[[list[dict]], list[dict]]


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
    frames_processed: int = 0
    events_raised: int = 0
    reports_filed: int = 0
    cooldowns: dict[str, float] = field(default_factory=dict)
    analyzer: SceneAnalyzer = field(default_factory=SceneAnalyzer)
    last_signals: dict = field(default_factory=dict)
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

        Used by the backend to persist events and file them as complaints.
        Both the HTTP (`analyze_frame`) and background-worker paths go through
        this, so events are durable regardless of which source drove the
        frame. The sink may return the same events enriched with auto-report
        fields; whatever it returns is what the caller sees.
        """
        self._event_sink = sink

    def _get_detector(self) -> YoloDetector:
        if self._detector is None:
            self._detector = YoloDetector.get_instance()
        return self._detector

    def preload(self) -> dict:
        """Load and warm the model ahead of the first frame."""
        return self._get_detector().status()

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
        session.frames_processed = 0
        session.events_raised = 0
        session.reports_filed = 0
        session.cooldowns = {}
        session.last_signals = {}
        # Fresh temporal state: carrying a background model or a fall track
        # across a source change would produce alarms about the transition
        # itself rather than about anything in the new scene.
        session.analyzer = SceneAnalyzer()

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
        once nothing is actually processing frames for it. Guarded by identity
        so a worker that already lost a start/stop race cannot clear a newer
        session's state."""
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
                "frames_processed": 0,
                "events_raised": 0,
                "reports_filed": 0,
                "signals": {},
            })
            return base
        base.update({
            "site_id": session.site_id,
            "active": session.active,
            "source_type": session.source_type,
            "people_count": session.people_count,
            "vehicle_count": session.vehicle_count,
            "last_frame_at": session.last_frame_at,
            "frames_processed": session.frames_processed,
            "events_raised": session.events_raised,
            "reports_filed": session.reports_filed,
            "signals": session.last_signals,
        })
        return base

    def process_frame(
        self,
        camera_id: str,
        site_id: str,
        frame_bgr: np.ndarray,
        enforce_min_interval: bool = True,
    ) -> dict:
        """Detection + scene analysis + rules for one frame.

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
        started = time.perf_counter()

        frame_bgr = _downscale(frame_bgr)

        detector = self._get_detector()
        detections = detector.detect(frame_bgr)
        signals = session.analyzer.analyze(frame_bgr, detections)

        session.people_count = sum(1 for d in detections if d.class_name == "person")
        session.vehicle_count = sum(
            1 for d in detections if d.class_name in hazard_rules.VEHICLE_CLASSES
        )
        session.frames_processed += 1
        session.last_signals = signals.to_dict()

        camera = camera_registry.get_camera(camera_id) or {
            "camera_id": camera_id,
            "camera_name": camera_id,
            "site_id": site_id,
            "rois": [],
        }
        drafts = hazard_rules.evaluate(detections, camera, signals)

        new_events: list[SafetyEvent] = []
        now_ts = _now()
        now_epoch = time.monotonic()
        for draft in drafts:
            last_fired = session.cooldowns.get(draft.dedupe_key, 0.0)
            if now_epoch - last_fired < draft.cooldown():
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
                hazard_class=draft.hazard_class,
                regions=draft.regions,
            ))
        session.events_raised += len(new_events)

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
            signals=session.last_signals,
        )
        result = analysis.to_dict()
        result["latency_ms"] = round((time.perf_counter() - started) * 1000.0, 1)

        if new_events and self._event_sink:
            try:
                enriched = self._event_sink(result["new_events"])
                if enriched:
                    result["new_events"] = enriched
                    session.reports_filed += sum(
                        1 for e in enriched if e.get("auto_report_id")
                    )
            except Exception:
                # Persistence or report filing must not break live inference -
                # the frontend still gets its detections and overlay this
                # frame, and the event is still returned, just without a
                # linked report.
                logger.exception("Vision event sink failed; continuing with live inference")

        return result

    @staticmethod
    def decode_base64_frame(image_base64: str) -> np.ndarray:
        if image_base64.strip().startswith("data:") and "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]
        try:
            raw = base64.b64decode(image_base64, validate=False)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"Frame payload is not valid base64: {exc}") from exc
        if not raw:
            raise ValueError("Frame payload was empty")
        arr = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Could not decode frame image data")
        return frame


def _downscale(frame: np.ndarray) -> np.ndarray:
    if frame is None or frame.size == 0:
        return frame
    h, w = frame.shape[:2]
    if w <= MAX_FRAME_WIDTH:
        return frame
    scale = MAX_FRAME_WIDTH / float(w)
    return cv2.resize(frame, (MAX_FRAME_WIDTH, max(1, int(h * scale))), interpolation=cv2.INTER_AREA)


class _BackgroundCaptureWorker(threading.Thread):
    """Best-effort background reader for an RTSP/IP-camera or local file source.

    Optional path: the demo does not depend on this working, since the
    frontend-driven webcam and upload paths are the primary and reliable ones.
    Holds at most the current frame (never a growing queue) and stops cleanly
    on `.stop()`.
    """

    def __init__(
        self,
        manager: VisionSessionManager,
        camera_id: str,
        site_id: str,
        source: str,
        target_fps: float = 4.0,
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
            failures = 0
            while not self._stop_event.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    # A dropped packet on an RTSP stream is normal; only give
                    # up after the source has failed repeatedly.
                    failures += 1
                    if failures >= 10:
                        self._mark_dead()
                        break
                    time.sleep(0.2)
                    continue
                failures = 0
                try:
                    self._manager.process_frame(
                        self._camera_id, self._site_id, frame, enforce_min_interval=False
                    )
                except Exception:
                    logger.exception("Background capture frame failed; continuing")
                time.sleep(self._interval)
        finally:
            cap.release()

    def _mark_dead(self) -> None:
        """The capture loop is ending on its own (source never opened, or reads
        kept failing) rather than via an explicit `.stop()` - without this the
        session would keep reporting `active: true` forever even though no
        frames are being processed, which would mislead the console."""
        self._manager.mark_worker_dead(self._camera_id, self)


_manager: Optional[VisionSessionManager] = None
_manager_lock = threading.Lock()


def get_manager() -> VisionSessionManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = VisionSessionManager()
        return _manager
