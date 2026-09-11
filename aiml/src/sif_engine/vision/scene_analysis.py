"""Frame-level scene analysis for mine / field CCTV hazard monitoring.

A COCO-pretrained YOLO model answers exactly one question: "which of these 80
everyday object classes are in this frame?". That is useful for *who* is in
the scene, but it cannot see the things that actually precede a mine or
field disaster — fire, smoke, a roof/rock fall, a worker collapsing, a dust
or gas cloud filling the frame. None of those are COCO classes.

This module supplies the missing half. It runs a small set of classical
computer-vision analyzers over each frame and maintains short temporal
history per camera, so the pipeline can reason about *change over time*
rather than one still image:

  FireSmokeAnalyzer      colour + flicker    -> open flame
                         desaturated moving  -> smoke plume
                         region texture      -> smoke vs. grey object
  VisibilityAnalyzer     edge energy trend   -> dust / smoke / gas obscuration
  PersonMonitor          tracked person boxes-> fall, collapse, immobility
  FallingObjectMonitor   motion blob descent -> dropped object / roof fall,
                                                and impact near a person

Design rules that the rest of the vision package depends on:

* **Recall over precision.** The brief for this system is explicit: a false
  alarm is acceptable, a missed disaster is not. Thresholds here are set to
  catch weak evidence, and every analyzer reports a graded score so the rule
  layer can attach a confidence rather than pretending the call is binary.
* **Never raise.** A malformed frame, a resolution change mid-stream or an
  OpenCV build without some codec must degrade to "no signal", never to a
  500 on a live camera feed.
* **Observation, not diagnosis.** Analyzers report what the pixels did
  ("a desaturated moving region covering 6% of frame with low edge energy").
  Turning that into "probable smoke from a fire" is the rule layer's job and
  is always carried as an inference a human confirms.
* **Bounded memory.** Every history is a fixed-length deque; a camera left
  running for a week must not grow.

Coordinates in and out of this module are normalized to 0..1 against the
frame, so they stay valid whatever resolution the source happens to be.
"""
from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Classical CV runs on a downscaled copy: at 480px wide the signals are
# identical for our purposes and the whole analyzer stack costs ~7 ms/frame,
# which keeps the per-frame budget dominated by YOLO rather than by this.
ANALYSIS_WIDTH = 480

# ---------------------------------------------------------------------------
# Fire — colour rule + temporal flicker
#
# The colour rule is the classic Chen/Celik style test (R dominant, hot and
# saturated) intersected with an HSV hue window. On its own it also fires on
# a hi-vis orange jacket, a sodium lamp or a red truck, so it is ANDed with a
# flicker measure: the fraction of the flame mask that changes between
# consecutive frames. A static orange object scores ~0; a real flame boundary
# churns constantly and scores 0.15-0.6.
# ---------------------------------------------------------------------------
FIRE_MIN_AREA = 0.0010      # 0.1% of frame — a burning sheet of paper at arm's length is far larger
# Measured separation on real footage is wide: a translating skin-toned or
# tan-coloured object (a face, a hi-vis jacket, painted plant) churns 0.03-0.09
# once its bulk motion is cancelled out, while a live flame churns 0.3-0.6.
# Sitting the gate at 0.18 keeps roughly a 3x margin on both sides rather than
# clipping the noise floor, where compression wobble alone can cross it.
FIRE_MIN_FLICKER = 0.18
FIRE_AREA_REF = 0.020       # area at which the area term saturates
# A flame is one contiguous body of light. Video compression, on the other
# hand, sprays isolated warm-coloured pixels across any textured surface, and
# those speckles churn violently frame to frame - so they pass a pure
# area-plus-flicker test. Requiring the largest connected component to be both
# big enough on its own AND to account for a real share of the lit pixels is
# what separates a flame from codec noise on a rock face.
FIRE_MIN_COMPONENT_AREA = 0.0006
FIRE_MIN_COMPONENT_SHARE = 0.35

# ---------------------------------------------------------------------------
# Smoke — desaturated, moving, and smoother than its surroundings
#
# Smoke is grey (low saturation), mid-brightness, in motion, and blurs the
# texture behind it, so its local edge energy is LOWER than the frame
# average. Regions covered by a detected person/vehicle are cut out first,
# which is what stops a worker in a grey overall from reading as a plume.
# ---------------------------------------------------------------------------
SMOKE_MIN_AREA = 0.012
SMOKE_AREA_REF = 0.090
SMOKE_MAX_SAT = 62
SMOKE_MIN_VAL = 55
SMOKE_MAX_VAL = 238
# Share of a grey region that has to be in motion for the whole region to
# count as a plume. Deliberately small: only the churning edge of a large
# slow-rolling cloud registers as motion, and demanding that the whole
# cloud move would shrink it to a rim that never crosses the area gate.
SMOKE_MIN_MOVING_SHARE = 0.04
# Smallest grey region worth considering as a plume, and how much blurrier
# than the rest of the frame it has to be. The texture ratio is what stops
# a whole desaturated scene from returning as one enormous plume: real
# smoke veils the detail behind it, an ordinary grey wall does not.
SMOKE_MIN_COMPONENT_AREA = 0.0015
SMOKE_MAX_TEXTURE_RATIO = 0.85

# Visibility: how far edge energy has to collapse against its own rolling
# baseline before the frame counts as obscured. 0.35 = "a third of the scene
# detail is gone", which is a dust cloud or a plume crossing the lens, not
# a lighting change.
VISIBILITY_DROP_TRIGGER = 0.35
VISIBILITY_BASELINE_FRAMES = 15

# Person fall geometry. A standing person's box is tall (h/w ~ 2-3); lying
# down it is wide (h/w < 1). `_FALL_LOOKBACK_S` bounds how far back we look
# for the "before" pose so a person who simply crouched slowly is not a fall.
FALL_LOOKBACK_S = 1.8
FALL_UPRIGHT_ASPECT = 1.15
FALL_PRONE_ASPECT = 0.95
FALL_DROP_SPEED = 0.30      # normalized frame-heights per second
FALL_FAST_DROP_SPEED = 0.55
IMMOBILE_AFTER_FALL_S = 2.0
IMMOBILE_MOVEMENT = 0.025

# Falling object / roof fall. Anything moving down faster than this, that is
# not a tracked person, is treated as a dropped or falling mass.
FALL_OBJECT_SPEED = 0.35        # normalized frame-heights per second, downward
# A mass descending onto a person is the highest-consequence case this
# module looks for, so the speed bar is deliberately lower there: missing a
# struck-by is far worse than raising one more alarm a controller dismisses.
FALL_OBJECT_SPEED_NEAR_PERSON = 0.20
FALL_OBJECT_MIN_AREA = 0.0006
FALL_OBJECT_MAX_AREA = 0.25
IMPACT_DISTANCE = 0.14      # normalized gap below which a falling mass counts as "at a person"

TRACK_MAX_AGE_S = 1.5
HISTORY_LEN = 12


def _clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else float(v))


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / union if union > 0 else 0.0


def _box_gap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """Shortest normalized gap between two boxes; 0.0 when they overlap."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    dx = max(0.0, max(bx1 - ax2, ax1 - bx2))
    dy = max(0.0, max(by1 - ay2, ay1 - by2))
    return math.hypot(dx, dy)


# ---------------------------------------------------------------------------
# Result contracts
# ---------------------------------------------------------------------------
@dataclass
class Region:
    """A contiguous area of the frame a pixel-level analyzer flagged."""
    kind: str  # fire | smoke
    bbox: tuple[float, float, float, float]
    score: float
    area_ratio: float

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "bbox": [round(v, 4) for v in self.bbox],
            "score": round(self.score, 3),
            "area_ratio": round(self.area_ratio, 5),
        }


@dataclass
class FallSignal:
    track_id: int
    kind: str  # fall | immobile
    bbox: tuple[float, float, float, float]
    drop_speed: float
    aspect_before: float
    aspect_after: float
    still_seconds: float = 0.0
    confidence: float = 0.5


@dataclass
class FallingObjectSignal:
    bbox: tuple[float, float, float, float]
    label: str            # the YOLO class when known, else "unidentified mass"
    descent_speed: float  # normalized frame-heights per second
    area_ratio: float
    near_person: bool
    person_bbox: Optional[tuple[float, float, float, float]] = None
    gap: float = 1.0
    confidence: float = 0.5


@dataclass
class SceneSignals:
    """Everything this module observed about one frame.

    Scores are graded 0..1 confidences, not booleans - `fire_active` and its
    siblings are the analyzer's own trigger decision, kept separate so the
    UI can show a rising score before anything actually fires.
    """
    fire_score: float = 0.0
    fire_active: bool = False
    fire_regions: list[Region] = field(default_factory=list)

    smoke_score: float = 0.0
    smoke_active: bool = False
    smoke_regions: list[Region] = field(default_factory=list)

    motion_score: float = 0.0
    visibility: float = 1.0
    visibility_drop: float = 0.0
    visibility_active: bool = False

    falls: list[FallSignal] = field(default_factory=list)
    falling_objects: list[FallingObjectSignal] = field(default_factory=list)

    person_count: int = 0
    occupancy_delta: int = 0
    crowd_event: Optional[str] = None  # surge | dispersal

    frame_index: int = 0
    analyzer_ready: bool = False

    def to_dict(self) -> dict:
        return {
            "fire_score": round(self.fire_score, 3),
            "smoke_score": round(self.smoke_score, 3),
            "motion_score": round(self.motion_score, 3),
            "visibility": round(self.visibility, 3),
            "visibility_drop": round(self.visibility_drop, 3),
            "fire_active": self.fire_active,
            "smoke_active": self.smoke_active,
            "visibility_active": self.visibility_active,
            "person_count": self.person_count,
            "occupancy_delta": self.occupancy_delta,
            "regions": [r.to_dict() for r in (self.fire_regions + self.smoke_regions)],
            "frame_index": self.frame_index,
            "analyzer_ready": self.analyzer_ready,
        }


# ---------------------------------------------------------------------------
# Fire & smoke
# ---------------------------------------------------------------------------
class FireSmokeAnalyzer:
    """Detects open flame and smoke plumes from colour, motion and texture."""

    def __init__(self):
        self._prev_fire_mask: Optional[np.ndarray] = None
        self._fire_hits = deque(maxlen=6)
        self._fire_area_history = deque(maxlen=8)
        self._smoke_area_history = deque(maxlen=8)

    @staticmethod
    def _fire_mask(bgr: np.ndarray, hsv: np.ndarray) -> np.ndarray:
        b, g, r = cv2.split(bgr)
        r16 = r.astype(np.int16)
        g16 = g.astype(np.int16)
        b16 = b.astype(np.int16)
        # Red channel dominant AND hot: a flame is the brightest red thing in
        # a frame, and its channels are ordered R > G > B with real margins.
        rule = (r16 > 150) & (r16 - g16 > 18) & (g16 - b16 > 8)
        h, s, v = cv2.split(hsv)
        # OpenCV hue is 0..179, so 0..30 covers red through yellow-orange.
        hue_ok = ((h <= 30) | (h >= 172)) & (s >= 60) & (v >= 140)
        mask = (rule & hue_ok).astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    @staticmethod
    def _centroid(mask: np.ndarray) -> Optional[tuple[float, float]]:
        m = cv2.moments(mask, binaryImage=True)
        if m["m00"] <= 0:
            return None
        return m["m10"] / m["m00"], m["m01"] / m["m00"]

    def _flicker(self, mask: np.ndarray) -> float:
        """How much the flame mask CHURNS, after cancelling out any bulk motion.

        This is the discriminator that separates a flame from every other
        flame-coloured thing on an industrial site. A naive frame-to-frame XOR
        is not enough: it scores near zero on a STATIC orange object (a painted
        pump, a sodium lamp) but very high on a MOVING one, because the leading
        and trailing edges of a translating rigid shape differ just as much as
        a flame boundary does - so a worker in a hi-vis jacket walking past the
        camera would read as a fire.

        Registering the previous mask onto the current one by its centroid
        shift first removes exactly that bulk translation. What survives is
        genuine shape change: a rigid body scores near zero however fast it
        moves, while a flame keeps churning because its outline is not rigid.
        The area of the mask is also tracked, since a flame pulses in size
        while a solid object does not.
        """
        prev = self._prev_fire_mask
        self._prev_fire_mask = mask
        area = int(np.count_nonzero(mask))
        self._fire_area_history.append(area)
        if prev is None or prev.shape != mask.shape or area == 0:
            return 0.0

        prev_c = self._centroid(prev)
        cur_c = self._centroid(mask)
        aligned = prev
        if prev_c and cur_c:
            dx = int(round(cur_c[0] - prev_c[0]))
            dy = int(round(cur_c[1] - prev_c[1]))
            if dx or dy:
                matrix = np.float32([[1, 0, dx], [0, 1, dy]])
                aligned = cv2.warpAffine(
                    prev, matrix, (prev.shape[1], prev.shape[0]),
                    flags=cv2.INTER_NEAREST, borderValue=0,
                )

        union_px = int(np.count_nonzero(cv2.bitwise_or(aligned, mask)))
        if union_px == 0:
            return 0.0
        churn = int(np.count_nonzero(cv2.bitwise_xor(aligned, mask))) / union_px

        # Area pulsing, relative to mean area over the recent window. A rigid
        # object holds a near-constant area; a flame does not.
        pulse = 0.0
        if len(self._fire_area_history) >= 4:
            areas = np.array(self._fire_area_history, dtype=np.float32)
            mean = float(areas.mean())
            if mean > 0:
                pulse = _clamp01(float(areas.std()) / mean / 0.25)

        return _clamp01(max(churn, 0.0) * 0.75 + pulse * 0.25)

    @staticmethod
    def _regions(mask: np.ndarray, kind: str, score: float, total_px: int, limit: int = 4) -> list[Region]:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = mask.shape[:2]
        out: list[Region] = []
        for c in sorted(contours, key=cv2.contourArea, reverse=True)[:limit]:
            area = cv2.contourArea(c)
            if area < total_px * 0.0004:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            out.append(Region(
                kind=kind,
                bbox=(x / w, y / h, (x + bw) / w, (y + bh) / h),
                score=score,
                area_ratio=area / total_px,
            ))
        return out

    def update(
        self,
        bgr: np.ndarray,
        hsv: np.ndarray,
        gray: np.ndarray,
        motion_mask: np.ndarray,
        occupied_mask: Optional[np.ndarray],
    ) -> tuple[float, bool, list[Region], float, bool, list[Region]]:
        total_px = bgr.shape[0] * bgr.shape[1]

        # ---- fire ---------------------------------------------------------
        fire_mask = self._fire_mask(bgr, hsv)
        fire_px = int(np.count_nonzero(fire_mask))
        fire_ratio = fire_px / total_px
        flicker = self._flicker(fire_mask)

        # Spatial coherence: how much of the lit area is one connected body.
        largest = 0.0
        if fire_px:
            contours, _ = cv2.findContours(fire_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                largest = max(cv2.contourArea(c) for c in contours)
        component_ratio = largest / total_px
        coherent = (
            component_ratio >= FIRE_MIN_COMPONENT_AREA
            and largest >= fire_px * FIRE_MIN_COMPONENT_SHARE
        )

        area_term = _clamp01(fire_ratio / FIRE_AREA_REF)
        flicker_term = _clamp01(flicker / 0.35)
        coherence_term = 1.0 if coherent else 0.25
        fire_score = _clamp01(area_term * (0.15 + 0.85 * flicker_term) * coherence_term)
        hit = fire_ratio >= FIRE_MIN_AREA and flicker >= FIRE_MIN_FLICKER and coherent
        self._fire_hits.append(1 if hit else 0)
        # Two hits inside the last six frames is enough. Demanding a long
        # unbroken run would miss exactly the short-lived ignition this
        # system exists to catch.
        fire_active = sum(self._fire_hits) >= 2
        fire_regions = self._regions(fire_mask, "fire", fire_score, total_px) if hit else []

        # ---- smoke --------------------------------------------------------
        # Smoke is grey, in motion, and blurs whatever is behind it. Testing
        # those three pixel by pixel badly under-detects, because only the
        # churning EDGE of a plume registers as motion and a large slow-rolling
        # cloud collapses to a thin rim that never reaches the area threshold.
        #
        # So candidate grey areas are found first as whole connected
        # components, and each component is judged as a unit on two questions:
        #
        #   is part of it moving?   - a static grey wall never is
        #   is it blurrier than       - this is what rejects the case the
        #   the rest of the frame?      component test would otherwise fail on,
        #                               a whole desaturated scene coming back as
        #                               one enormous "plume"
        #
        # Both are computed with label-wise sums in one pass rather than per
        # component masking, so the cost does not grow with component count.
        lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
        h, s, v = cv2.split(hsv)
        greyish = (
            (s <= SMOKE_MAX_SAT) & (v >= SMOKE_MIN_VAL) & (v <= SMOKE_MAX_VAL)
        ).astype(np.uint8) * 255
        if occupied_mask is not None:
            # People and vehicles are grey and they move; cutting their boxes
            # out is what keeps a worker in a grey overall from reading as a
            # plume.
            greyish = cv2.bitwise_and(greyish, cv2.bitwise_not(occupied_mask))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        greyish = cv2.morphologyEx(greyish, cv2.MORPH_OPEN, kernel)
        greyish = cv2.morphologyEx(greyish, cv2.MORPH_CLOSE, kernel)

        # The seed is MOTION, not greyness. In an underground or low-light
        # scene almost every pixel is desaturated, so a component search over
        # the grey mask alone returns one component covering the whole frame
        # and isolates nothing. What actually distinguishes a plume is that it
        # CHANGED - so start from the background-subtractor foreground,
        # restricted to grey pixels.
        seed = cv2.bitwise_and(greyish, motion_mask)
        # Then close aggressively. Only the churning rim of a slow-rolling
        # cloud registers as foreground; a large close bridges that rim into
        # the solid body it encloses, which is what lets the plume be measured
        # at its true size instead of as a thin outline.
        seed = cv2.morphologyEx(
            seed, cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)),
        )
        # Re-intersect with grey so the close cannot spill the plume out over
        # coloured plant or a hi-vis worker standing next to it.
        seed = cv2.bitwise_and(seed, greyish)

        smoke_mask = np.zeros_like(greyish)
        num, labels, stats, _ = cv2.connectedComponentsWithStats(seed, connectivity=8)
        if num > 1:
            flat = labels.ravel()
            counts = np.bincount(flat, minlength=num).astype(np.float64)
            edge_sums = np.bincount(flat, weights=lap.ravel(), minlength=num)
            move_sums = np.bincount(
                flat, weights=(motion_mask.ravel() > 0).astype(np.float64), minlength=num
            )
            total_edge = float(lap.sum())
            total_count = float(lap.size)

            for idx in range(1, num):
                comp_area = float(counts[idx])
                if comp_area < total_px * SMOKE_MIN_COMPONENT_AREA:
                    continue
                if move_sums[idx] < comp_area * SMOKE_MIN_MOVING_SHARE:
                    # Belt and braces after the close: a component that ended
                    # up with essentially no original foreground in it came
                    # entirely from bridging and is not a plume.
                    continue
                outside_count = total_count - comp_area
                if outside_count <= 0:
                    continue
                inside_energy = edge_sums[idx] / comp_area
                outside_energy = (total_edge - edge_sums[idx]) / outside_count
                if inside_energy >= outside_energy * SMOKE_MAX_TEXTURE_RATIO:
                    continue
                smoke_mask[labels == idx] = 255

        smoke_px = int(np.count_nonzero(smoke_mask))
        smoke_ratio = smoke_px / total_px

        texture_term = 0.5
        if smoke_px > 0:
            frame_energy = float(lap.mean()) + 1e-6
            region_energy = float(lap[smoke_mask > 0].mean())
            # Smoke veils the texture behind it, so its edge energy sits well
            # below the frame average. Ratio 1.0 -> not smoke-like, 0.3 -> very.
            texture_term = _clamp01(1.0 - (region_energy / frame_energy) / 0.9)

        self._smoke_area_history.append(smoke_ratio)
        growth_term = 0.0
        if len(self._smoke_area_history) >= 4:
            early = float(np.mean(list(self._smoke_area_history)[:2]))
            late = float(np.mean(list(self._smoke_area_history)[-2:]))
            growth_term = _clamp01((late - early) / max(early, 0.01))

        area_term = _clamp01(smoke_ratio / SMOKE_AREA_REF)
        smoke_score = _clamp01(area_term * (0.45 + 0.35 * texture_term + 0.20 * growth_term))
        smoke_active = smoke_ratio >= SMOKE_MIN_AREA
        smoke_regions = self._regions(smoke_mask, "smoke", smoke_score, total_px) if smoke_active else []

        # Areas the falling-mass detector must ignore, computed from the raw
        # masks rather than from the reported regions. Fire and smoke both
        # churn constantly, so their motion blobs read as descending masses -
        # and the reported regions are only populated on a frame that actually
        # triggered, which would leave every non-triggering frame unprotected.
        suppress = self._regions(fire_mask, "fire", fire_score, total_px, limit=6)
        suppress += self._regions(smoke_mask, "smoke", smoke_score, total_px, limit=6)

        return (
            fire_score, fire_active, fire_regions,
            smoke_score, smoke_active, smoke_regions,
            [r.bbox for r in suppress],
        )


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------
@dataclass
class _Track:
    track_id: int
    label: str
    bbox: tuple[float, float, float, float]
    history: deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))
    last_seen: float = 0.0
    missed: int = 0
    fall_reported: bool = False
    fallen_at: Optional[float] = None
    immobile_reported: bool = False
    descent_reported: bool = False

    def centroid(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0

    def aspect(self) -> float:
        x1, y1, x2, y2 = self.bbox
        w = max(x2 - x1, 1e-4)
        return (y2 - y1) / w


class _Tracker:
    """Minimal IoU-then-distance tracker.

    Deliberately not a Kalman/ByteTrack implementation: at the 2-3 fps this
    pipeline runs at, and for the questions being asked of it (did this box
    drop fast, did it go from tall to wide), greedy association is both
    sufficient and far easier to reason about when a judge asks how it works.
    Tolerates short gaps so one missed detection does not restart a track and
    erase the history a fall test depends on.
    """

    def __init__(self, iou_threshold: float = 0.20, max_distance: float = 0.18):
        self._tracks: dict[int, _Track] = {}
        self._next_id = 1
        self._iou_threshold = iou_threshold
        self._max_distance = max_distance

    @property
    def tracks(self) -> list[_Track]:
        return list(self._tracks.values())

    def update(self, boxes, now: float) -> list[_Track]:
        unmatched = set(self._tracks.keys())
        updated: list[_Track] = []

        for label, bbox in boxes:
            best_id, best_score = None, 0.0
            for tid in unmatched:
                score = _iou(self._tracks[tid].bbox, bbox)
                if score > best_score:
                    best_id, best_score = tid, score
            if best_id is None or best_score < self._iou_threshold:
                # Fast movement between frames can leave two boxes with no
                # overlap at all, which is precisely the case a fall creates -
                # fall back to nearest centre within a bounded radius.
                cx, cy = (bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0
                best_dist = self._max_distance
                cand = None
                for tid in unmatched:
                    tcx, tcy = self._tracks[tid].centroid()
                    d = math.hypot(cx - tcx, cy - tcy)
                    if d < best_dist:
                        best_dist, cand = d, tid
                best_id = cand

            if best_id is None:
                track = _Track(track_id=self._next_id, label=label, bbox=bbox, last_seen=now)
                self._next_id += 1
                self._tracks[track.track_id] = track
            else:
                unmatched.discard(best_id)
                track = self._tracks[best_id]
                track.bbox = bbox
                track.label = label
                track.last_seen = now
                track.missed = 0

            x1, y1, x2, y2 = bbox
            track.history.append((now, (x1 + x2) / 2.0, (y1 + y2) / 2.0, x2 - x1, y2 - y1))
            updated.append(track)

        for tid in list(unmatched):
            self._tracks[tid].missed += 1
        for tid, track in list(self._tracks.items()):
            if now - track.last_seen > TRACK_MAX_AGE_S:
                del self._tracks[tid]
        return updated


class PersonMonitor:
    """Turns tracked person boxes into fall / collapse / immobility signals."""

    def __init__(self):
        self._tracker = _Tracker(iou_threshold=0.20, max_distance=0.22)
        self._last_count = 0

    def update(self, person_boxes, now: float):
        tracks = self._tracker.update([("person", b) for b in person_boxes], now)
        signals: list[FallSignal] = []

        for track in tracks:
            hist = list(track.history)
            if len(hist) < 2:
                continue
            t_now, cx, cy, w, h = hist[-1]
            aspect_now = h / max(w, 1e-4)

            # Reference pose: the newest sample that is at least 0.25 s old and
            # no older than FALL_LOOKBACK_S. Anything slower than that window
            # is someone crouching or sitting down, not falling.
            ref = None
            for sample in reversed(hist[:-1]):
                age = t_now - sample[0]
                if 0.25 <= age <= FALL_LOOKBACK_S:
                    ref = sample
                    break
            if ref is None:
                continue
            t_ref, rcx, rcy, rw, rh = ref
            dt = max(t_now - t_ref, 1e-3)
            aspect_ref = rh / max(rw, 1e-4)
            drop_speed = (cy - rcy) / dt  # positive = moving down the frame

            posture_collapse = aspect_ref >= FALL_UPRIGHT_ASPECT and aspect_now <= FALL_PRONE_ASPECT
            rapid_shrink = aspect_now < aspect_ref * 0.72 and drop_speed >= FALL_DROP_SPEED
            free_drop = drop_speed >= FALL_FAST_DROP_SPEED

            if not track.fall_reported and (posture_collapse or rapid_shrink or free_drop):
                confidence = 0.55
                if posture_collapse:
                    confidence = 0.80
                    if drop_speed >= FALL_DROP_SPEED:
                        confidence = 0.90
                elif free_drop:
                    confidence = 0.72
                track.fall_reported = True
                track.fallen_at = t_now
                signals.append(FallSignal(
                    track_id=track.track_id,
                    kind="fall",
                    bbox=track.bbox,
                    drop_speed=round(drop_speed, 3),
                    aspect_before=round(aspect_ref, 2),
                    aspect_after=round(aspect_now, 2),
                    confidence=confidence,
                ))
                continue

            # A person who went down and then stopped moving is the case that
            # separates "slipped and got straight up" from "needs a rescue".
            if track.fall_reported and not track.immobile_reported and track.fallen_at is not None:
                still_for = t_now - track.fallen_at
                if still_for >= IMMOBILE_AFTER_FALL_S:
                    recent = [s for s in hist if t_now - s[0] <= IMMOBILE_AFTER_FALL_S]
                    if len(recent) >= 2:
                        movement = max(
                            math.hypot(s[1] - recent[0][1], s[2] - recent[0][2])
                            for s in recent
                        )
                        if movement <= IMMOBILE_MOVEMENT:
                            track.immobile_reported = True
                            signals.append(FallSignal(
                                track_id=track.track_id,
                                kind="immobile",
                                bbox=track.bbox,
                                drop_speed=0.0,
                                aspect_before=round(aspect_ref, 2),
                                aspect_after=round(aspect_now, 2),
                                still_seconds=round(still_for, 1),
                                confidence=0.85,
                            ))

        count = len(person_boxes)
        delta = count - self._last_count
        crowd_event = None
        # A change of three or more people between consecutive frames at ~2 fps
        # is not people walking - it is a rush toward or away from something.
        if delta >= 3:
            crowd_event = "surge"
        elif delta <= -3 and self._last_count >= 4:
            crowd_event = "dispersal"
        self._last_count = count
        return signals, count, crowd_event, delta


class FallingObjectMonitor:
    """Detects masses moving down the frame, and impacts near a person.

    Two sources feed this. Named YOLO detections cover the case where the
    falling thing happens to be a COCO class. Motion blobs cover everything
    else - a rock, a section of roof, a length of pipe, a dropped tool - none
    of which any pretrained detector recognises, and all of which are exactly
    what kills people underground.

    Blobs overlapping a person, a flame or a plume are dropped before tracking.
    A worker walking downhill in frame is not a roof fall, and neither is a
    flame front: fire and smoke both churn constantly, so their motion blobs
    otherwise register as a mass descending through the scene and every fire
    would raise a spurious roof-fall alarm alongside the real fire alarm.
    """

    def __init__(self):
        self._tracker = _Tracker(iou_threshold=0.10, max_distance=0.30)

    @staticmethod
    def _blobs(motion_mask: np.ndarray, exclude: list[tuple[float, float, float, float]]):
        contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = motion_mask.shape[:2]
        total = float(h * w)
        out = []
        for c in contours:
            area = cv2.contourArea(c)
            ratio = area / total
            if ratio < FALL_OBJECT_MIN_AREA or ratio > FALL_OBJECT_MAX_AREA:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            bbox = (x / w, y / h, (x + bw) / w, (y + bh) / h)
            # Excluded either by real overlap, or by sitting inside an excluded
            # area: a flame front throws off many small blobs that individually
            # score a low IoU against the flame region but are plainly part of
            # it, and each one would otherwise become its own falling mass.
            bcx, bcy = (bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0
            if any(
                _iou(bbox, ex) > 0.25
                or (ex[0] <= bcx <= ex[2] and ex[1] <= bcy <= ex[3])
                for ex in exclude
            ):
                continue
            out.append((bbox, ratio))
        return out

    def update(self, motion_mask, named_objects, person_boxes, now: float, exclude_regions=None):
        blobs = self._blobs(motion_mask, list(person_boxes) + list(exclude_regions or []))
        candidates = [("mass", b) for b, _ in blobs] + [(lbl, bb) for lbl, bb in named_objects]
        tracks = self._tracker.update(candidates, now)
        area_by_box = {b: r for b, r in blobs}

        signals: list[FallingObjectSignal] = []
        for track in tracks:
            hist = list(track.history)
            if len(hist) < 2 or track.descent_reported:
                continue
            t_now, cx, cy, w, h = hist[-1]
            ref = None
            for sample in reversed(hist[:-1]):
                age = t_now - sample[0]
                if 0.15 <= age <= 1.2:
                    ref = sample
                    break
            if ref is None:
                continue
            dt = max(t_now - ref[0], 1e-3)
            descent = (cy - ref[2]) / dt
            horizontal = abs(cx - ref[1]) / dt

            gap, near_box = 1.0, None
            for pb in person_boxes:
                d = _box_gap(track.bbox, pb)
                if d < gap:
                    gap, near_box = d, pb
            near = gap <= IMPACT_DISTANCE and near_box is not None

            if descent < (FALL_OBJECT_SPEED_NEAR_PERSON if near else FALL_OBJECT_SPEED):
                continue
            # A mass that is mostly going sideways is a vehicle or a person in
            # the distance, not something under gravity.
            if horizontal > descent * 1.2:
                continue

            track.descent_reported = True
            area_ratio = area_by_box.get(track.bbox, max(w * h, 0.0))
            confidence = _clamp01(0.45 + 0.35 * _clamp01(descent / 1.2) + (0.20 if near else 0.0))
            signals.append(FallingObjectSignal(
                bbox=track.bbox,
                label=track.label if track.label != "mass" else "unidentified mass",
                descent_speed=round(descent, 3),
                area_ratio=round(area_ratio, 5),
                near_person=near,
                person_bbox=near_box if near else None,
                gap=round(gap, 3),
                confidence=confidence,
            ))
        return signals


class VisibilityAnalyzer:
    """Tracks how much scene detail is being lost.

    Dust from a blast or a collapse, a smoke layer, or a released gas cloud
    all do the same thing to a camera: they wash out edges. Comparing current
    edge energy against a slow rolling baseline of the same camera detects
    that without needing to know what the obscurant is - and without firing
    on a scene that was simply always low-contrast, because the baseline is
    per camera rather than absolute.
    """

    def __init__(self):
        self._baseline: Optional[float] = None
        self._frames = 0

    def update(self, gray: np.ndarray) -> tuple[float, float, bool, bool]:
        energy = float(cv2.Laplacian(gray, cv2.CV_32F, ksize=3).var())
        self._frames += 1
        if self._baseline is None:
            self._baseline = energy
            return 1.0, 0.0, False, False

        ready = self._frames >= VISIBILITY_BASELINE_FRAMES
        drop = _clamp01(1.0 - energy / max(self._baseline, 1e-3))
        visibility = _clamp01(energy / max(self._baseline, 1e-3))

        # Adapt slowly, and much more slowly while obscured - otherwise the
        # baseline chases the dust cloud down and the alarm silently clears
        # itself while the scene is still unusable.
        alpha = 0.02 if drop >= VISIBILITY_DROP_TRIGGER else 0.10
        self._baseline = (1 - alpha) * self._baseline + alpha * energy
        return visibility, drop, bool(ready and drop >= VISIBILITY_DROP_TRIGGER), ready


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
class SceneAnalyzer:
    """One per camera. Feed it every frame plus that frame's detections."""

    def __init__(self):
        self._fire_smoke = FireSmokeAnalyzer()
        self._persons = PersonMonitor()
        self._objects = FallingObjectMonitor()
        self._visibility = VisibilityAnalyzer()
        self._bg = cv2.createBackgroundSubtractorMOG2(
            history=250, varThreshold=28, detectShadows=False
        )
        self._frame_index = 0

    def reset(self) -> None:
        self.__init__()

    def analyze(self, frame_bgr: np.ndarray, detections) -> SceneSignals:
        """Return every scene-level signal for one frame.

        `detections` is the detector output for the SAME frame; person boxes
        steer the smoke mask, the blob filter and the impact test, so passing
        a stale list would quietly degrade all three.
        """
        signals = SceneSignals()
        if frame_bgr is None or frame_bgr.size == 0:
            return signals
        try:
            self._frame_index += 1
            signals.frame_index = self._frame_index
            now = time.monotonic()

            h, w = frame_bgr.shape[:2]
            if w > ANALYSIS_WIDTH:
                scale = ANALYSIS_WIDTH / float(w)
                small = cv2.resize(frame_bgr, (ANALYSIS_WIDTH, max(1, int(h * scale))),
                                   interpolation=cv2.INTER_AREA)
            else:
                small = frame_bgr
            sh, sw = small.shape[:2]

            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

            motion = self._bg.apply(small)
            motion = cv2.morphologyEx(
                motion, cv2.MORPH_OPEN,
                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
            )
            motion = cv2.dilate(motion, np.ones((3, 3), np.uint8), iterations=1)
            signals.motion_score = _clamp01(float(np.count_nonzero(motion)) / (sh * sw))

            person_boxes = [d.bbox for d in detections if d.class_name == "person"]
            named_objects = [
                (d.class_name, d.bbox) for d in detections if d.class_name != "person"
            ]

            occupied = None
            if detections:
                occupied = np.zeros((sh, sw), dtype=np.uint8)
                for d in detections:
                    x1, y1, x2, y2 = d.bbox
                    # Pad the cut-out: a persons silhouette is narrower than
                    # the box only in the middle, and smoke hugging a body
                    # edge would otherwise survive the mask.
                    px1 = max(0, int((x1 - 0.02) * sw))
                    py1 = max(0, int((y1 - 0.02) * sh))
                    px2 = min(sw, int((x2 + 0.02) * sw))
                    py2 = min(sh, int((y2 + 0.02) * sh))
                    if px2 > px1 and py2 > py1:
                        occupied[py1:py2, px1:px2] = 255

            (signals.fire_score, signals.fire_active, signals.fire_regions,
             signals.smoke_score, signals.smoke_active, signals.smoke_regions,
             suppress_regions) = self._fire_smoke.update(
                small, hsv, gray, motion, occupied
            )

            (signals.visibility, signals.visibility_drop,
             signals.visibility_active, ready) = self._visibility.update(gray)
            signals.analyzer_ready = ready

            falls, count, crowd, delta = self._persons.update(person_boxes, now)
            signals.falls = falls
            signals.person_count = count
            signals.crowd_event = crowd
            signals.occupancy_delta = delta

            signals.falling_objects = self._objects.update(
                motion, named_objects, person_boxes, now,
                exclude_regions=suppress_regions,
            )
        except Exception:
            # A live camera must not be able to 500 the API because one frame
            # had an unexpected shape or an OpenCV call disagreed with it.
            logger.exception("Scene analysis failed on one frame; treating it as no signal")
        return signals
