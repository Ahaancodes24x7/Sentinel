import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  Camera as CameraIcon,
  CheckCircle2,
  FileText,
  Film,
  Flame,
  Loader2,
  PersonStanding,
  Radio,
  Upload,
  Video,
  Wind,
  Webcam,
} from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { cn } from '../lib/cn';
import { useSelectedSite } from '../lib/siteContext';
import { api } from '../api/client';
import {
  useAutoFiledReports,
  useVisionAcknowledge,
  useVisionCameras,
  useVisionEvents,
  useVisionStart,
  useVisionStatus,
  useVisionStop,
} from '../api/hooks';
import type {
  VisionAnalyzeFrameResponse,
  VisionDetectedObject,
  VisionRegion,
  VisionSafetyEvent,
  VisionSignals,
  VisionSourceType,
} from '../api/types';
import {
  VISION_EVENT_LABEL,
  VISION_PRIORITY_TONE,
  VISION_SEVERITY_TONE,
} from '../api/types';
import { Bar, Chip, Counter, LiveFeed, PanelHead, PulseDot, ScanPanel } from '../components/kinetic';
import { Hint, HelpDot } from '../components/common/Hint';
import { EmptyPanel, QueryError } from '../components/common/QueryState';

/* --------------------------------------------------------------------------
 * Camera Watch
 *
 * Everything on this page — the video, the boxes, the hazard indices, the
 * events, the complaints filed on the right — comes from a real round trip
 * with the backend detector and rule engine. No timer fabricates a count or
 * an event; if the analyse loop stops, every number stops moving.
 *
 * Two things here are worth knowing before changing them:
 *
 * 1. The analyse loop is SELF-SCHEDULING, not a setInterval. With an interval,
 *    a frame that takes longer than the tick stacks the next request on top of
 *    it, and the backlog only grows: the server ends up processing frames from
 *    several seconds ago while the queue keeps building. Chaining the next
 *    capture off the previous response instead means the page naturally runs
 *    at whatever rate the pipeline can actually sustain.
 *
 * 2. Overlay geometry is computed against the video's DISPLAYED CONTENT BOX,
 *    not its element box. The element is `object-contain`, so a 4:3 webcam
 *    inside a 16:9 frame is pillarboxed and the picture occupies only part of
 *    the element. Drawing normalized boxes across the full element width puts
 *    every bounding box in the wrong place and stretched — see contentRect().
 * ----------------------------------------------------------------------- */

const TARGET_INTERVAL_MS = 320;
const CAPTURE_WIDTH = 640;

const EMPTY_SIGNALS: VisionSignals = {
  fire_score: 0,
  smoke_score: 0,
  motion_score: 0,
  visibility: 1,
  visibility_drop: 0,
  fire_active: false,
  smoke_active: false,
  visibility_active: false,
  person_count: 0,
  occupancy_delta: 0,
  regions: [],
  frame_index: 0,
  analyzer_ready: false,
};

function roiStrokeColor(roiType: string): string {
  if (roiType === 'restricted_zone') return 'rgba(239,68,68,0.95)';
  if (roiType === 'lifting_zone') return 'rgba(245,158,11,0.95)';
  return 'rgba(56,189,248,0.85)';
}

const REGION_STYLE: Record<string, { stroke: string; label: string }> = {
  fire: { stroke: '#ff5a1f', label: 'FIRE' },
  smoke: { stroke: '#9aa6b2', label: 'SMOKE' },
  falling: { stroke: '#f59e0b', label: 'FALLING MASS' },
  casualty: { stroke: '#ef4444', label: 'PERSON DOWN' },
};

/**
 * Where the video picture actually sits inside its element.
 *
 * `object-contain` letterboxes or pillarboxes the picture to preserve aspect
 * ratio, so the drawable area is generally smaller than the element and offset
 * within it. Every overlay coordinate is mapped through this.
 */
function contentRect(video: HTMLVideoElement) {
  const ew = video.clientWidth || 1;
  const eh = video.clientHeight || 1;
  const vw = video.videoWidth;
  const vh = video.videoHeight;
  if (!vw || !vh) return { x: 0, y: 0, w: ew, h: eh, ew, eh };
  const scale = Math.min(ew / vw, eh / vh);
  const w = vw * scale;
  const h = vh * scale;
  return { x: (ew - w) / 2, y: (eh - h) / 2, w, h, ew, eh };
}

export function LiveVisionPage() {
  const { selectedSite } = useSelectedSite();

  const { data: camerasData, isLoading: camerasLoading, error: camerasError } = useVisionCameras(
    selectedSite.site_id,
  );
  const cameras = useMemo(() => camerasData?.cameras ?? [], [camerasData]);
  const [cameraId, setCameraId] = useState<string>('');

  useEffect(() => {
    if (cameras.length && !cameras.some((c) => c.camera_id === cameraId)) {
      setCameraId(cameras[0].camera_id);
    }
  }, [cameras, cameraId]);

  const camera = cameras.find((c) => c.camera_id === cameraId);

  const [sourceType, setSourceType] = useState<VisionSourceType>('demo_video');
  const [rtspUrl, setRtspUrl] = useState('');
  const [videoObjectUrl, setVideoObjectUrl] = useState<string | null>(null);
  const [videoFileName, setVideoFileName] = useState<string | null>(null);
  const [active, setActive] = useState(false);
  const [starting, setStarting] = useState(false);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [lastDetections, setLastDetections] = useState<VisionDetectedObject[]>([]);
  const [signals, setSignals] = useState<VisionSignals>(EMPTY_SIGNALS);
  const [latency, setLatency] = useState(0);
  const [selectedEvent, setSelectedEvent] = useState<VisionSafetyEvent | null>(null);
  const [alarm, setAlarm] = useState<VisionSafetyEvent | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const captureRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  // The loop is driven by a chained timeout rather than an interval, and these
  // refs are what let a running loop see the current camera/site and be told to
  // stop without being re-created on every state change.
  const loopTimerRef = useRef<number | null>(null);
  const runningRef = useRef(false);
  const ctxRef = useRef({ cameraId: '', siteId: '' });
  ctxRef.current = { cameraId, siteId: selectedSite.site_id };

  const startMutation = useVisionStart();
  const stopMutation = useVisionStop();
  const acknowledge = useVisionAcknowledge();
  const statusQuery = useVisionStatus(cameraId, Boolean(cameraId));
  const eventsQuery = useVisionEvents(cameraId, 40, Boolean(cameraId));
  const autoReports = useAutoFiledReports(selectedSite.canonical_name, 12);

  const status = statusQuery.data;
  const events = eventsQuery.data?.events ?? [];
  const filedReports = autoReports.data?.items ?? [];

  const stopCaptureLoop = useCallback(() => {
    runningRef.current = false;
    if (loopTimerRef.current !== null) {
      window.clearTimeout(loopTimerRef.current);
      loopTimerRef.current = null;
    }
  }, []);

  const drawOverlay = useCallback(
    (detections: VisionDetectedObject[], regions: VisionRegion[]) => {
      const canvas = overlayRef.current;
      const video = videoRef.current;
      if (!canvas || !video) return;

      const rect = contentRect(video);
      // Back the canvas at device resolution so 1px strokes and 11px labels
      // stay crisp on a HiDPI screen instead of resampling to mush.
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      if (canvas.width !== Math.round(rect.ew * dpr) || canvas.height !== Math.round(rect.eh * dpr)) {
        canvas.width = Math.round(rect.ew * dpr);
        canvas.height = Math.round(rect.eh * dpr);
      }
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, rect.ew, rect.eh);

      const px = (nx: number) => rect.x + nx * rect.w;
      const py = (ny: number) => rect.y + ny * rect.h;

      (camera?.rois ?? []).forEach((roi) => {
        const color = roiStrokeColor(roi.roi_type);
        ctx.beginPath();
        roi.points.forEach(([x, y], i) => {
          if (i === 0) ctx.moveTo(px(x), py(y));
          else ctx.lineTo(px(x), py(y));
        });
        ctx.closePath();
        ctx.setLineDash([6, 4]);
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = color;
        ctx.stroke();
        ctx.fillStyle = color.replace(/0\.\d+\)/, '0.07)');
        ctx.fill();
        ctx.setLineDash([]);
        ctx.font = '10px ui-monospace, monospace';
        ctx.fillStyle = color;
        const [lx, ly] = roi.points[0];
        ctx.fillText(roi.name, px(lx) + 4, py(ly) + 12);
      });

      // Scene regions under the detection boxes: a flame or plume is context
      // for the people in front of it, not the other way round.
      regions.forEach((region) => {
        const style = REGION_STYLE[region.kind] ?? { stroke: '#d4ff3f', label: region.kind.toUpperCase() };
        const [x1, y1, x2, y2] = region.bbox;
        ctx.lineWidth = 2;
        ctx.strokeStyle = style.stroke;
        ctx.setLineDash([3, 3]);
        ctx.strokeRect(px(x1), py(y1), (x2 - x1) * rect.w, (y2 - y1) * rect.h);
        ctx.setLineDash([]);
        ctx.fillStyle = `${style.stroke}22`;
        ctx.fillRect(px(x1), py(y1), (x2 - x1) * rect.w, (y2 - y1) * rect.h);
        ctx.font = 'bold 10px ui-monospace, monospace';
        ctx.fillStyle = style.stroke;
        ctx.fillText(style.label, px(x1) + 3, Math.max(10, py(y1) - 4));
      });

      detections.forEach((d) => {
        const [x1, y1, x2, y2] = d.bbox;
        const bx = px(x1);
        const by = py(y1);
        const bw = (x2 - x1) * rect.w;
        const bh = (y2 - y1) * rect.h;
        const color = d.class_name === 'person' ? '#d4ff3f' : '#38bdf8';
        ctx.lineWidth = 2;
        ctx.strokeStyle = color;
        ctx.strokeRect(bx, by, bw, bh);
        const label = `${d.class_name} ${(d.confidence * 100).toFixed(0)}%`;
        ctx.font = '10px ui-monospace, monospace';
        const textW = ctx.measureText(label).width + 6;
        ctx.fillStyle = color;
        ctx.fillRect(bx, Math.max(0, by - 13), textW, 13);
        ctx.fillStyle = '#0a0a0a';
        ctx.fillText(label, bx + 3, Math.max(9, by - 3));
      });
    },
    [camera],
  );

  const analyzeOnce = useCallback(async () => {
    const video = videoRef.current;
    const capture = captureRef.current;
    const { cameraId: camId, siteId } = ctxRef.current;
    if (!video || !capture || !camId || video.readyState < 2 || !video.videoWidth) return;

    const targetW = CAPTURE_WIDTH;
    const targetH = Math.round(targetW * (video.videoHeight / video.videoWidth));
    capture.width = targetW;
    capture.height = targetH;
    const ctx = capture.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, targetW, targetH);
    const dataUrl = capture.toDataURL('image/jpeg', 0.62);

    try {
      const res = await api.post<VisionAnalyzeFrameResponse>('/vision/analyze-frame', {
        site_id: siteId,
        camera_id: camId,
        image_base64: dataUrl,
      });
      // A skipped frame means the server-side rate limit rejected it; the
      // previous overlay stays on screen rather than blinking to empty.
      if (res.skipped) return;
      setLastDetections(res.detections);
      setSignals(res.signals ?? EMPTY_SIGNALS);
      setLatency(res.latency_ms ?? 0);
      drawOverlay(res.detections, res.signals?.regions ?? []);

      if (res.new_events.length) {
        const worst =
          res.new_events.find((e) => e.severity === 'critical') ?? res.new_events[0];
        setAlarm(worst);
        window.setTimeout(() => setAlarm((cur) => (cur === worst ? null : cur)), 6000);
        eventsQuery.refetch();
        statusQuery.refetch();
        autoReports.refetch();
      }
    } catch {
      // A transient network hiccup must not stop the loop or show a fake
      // state; the next tick simply tries again.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [drawOverlay]);

  const runLoop = useCallback(async () => {
    if (!runningRef.current) return;
    const started = performance.now();
    await analyzeOnce();
    if (!runningRef.current) return;
    // Chain the next capture off this one, and never queue two at once: the
    // page settles at whatever rate the pipeline can actually sustain.
    const wait = Math.max(60, TARGET_INTERVAL_MS - (performance.now() - started));
    loopTimerRef.current = window.setTimeout(runLoop, wait);
  }, [analyzeOnce]);

  const handleStop = useCallback(() => {
    setActive(false);
    stopCaptureLoop();
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    const video = videoRef.current;
    if (video) {
      video.pause();
      video.srcObject = null;
    }
    const { cameraId: camId } = ctxRef.current;
    if (camId) stopMutation.mutate({ camera_id: camId });
    const canvas = overlayRef.current;
    canvas?.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height);
    setLastDetections([]);
    setSignals(EMPTY_SIGNALS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stopCaptureLoop]);

  // Switching site or camera ends whatever session was running — analysing a
  // feed under the wrong camera's zones is worse than requiring a fresh Start.
  useEffect(() => {
    handleStop();
    setSelectedEvent(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameraId, selectedSite.site_id]);

  useEffect(
    () => () => {
      stopCaptureLoop();
      streamRef.current?.getTracks().forEach((t) => t.stop());
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    },
    [stopCaptureLoop],
  );

  // Keep the overlay registered with the video box across window resizes and
  // sidebar collapses; without this the boxes drift until the next frame.
  useEffect(() => {
    const onResize = () => drawOverlay(lastDetections, signals.regions ?? []);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [drawOverlay, lastDetections, signals.regions]);

  function handleFileSelected(file: File) {
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    const url = URL.createObjectURL(file);
    objectUrlRef.current = url;
    setVideoObjectUrl(url);
    setVideoFileName(file.name);
  }

  async function handleStart() {
    if (!camera) return;
    setCaptureError(null);
    setStarting(true);
    try {
      const video = videoRef.current;
      if (sourceType === 'webcam') {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        });
        streamRef.current = stream;
        if (video) {
          // removeAttribute, not src = '': assigning an empty string makes the
          // element resolve it against the page URL and fire a load error.
          video.removeAttribute('src');
          video.load();
          video.srcObject = stream;
          video.loop = false;
          await video.play();
        }
      } else if (sourceType === 'demo_video') {
        if (!videoObjectUrl || !video) {
          setCaptureError('Choose a video file first.');
          setStarting(false);
          return;
        }
        video.srcObject = null;
        video.src = videoObjectUrl;
        video.loop = true;
        await video.play();
      }

      await startMutation.mutateAsync({
        site_id: selectedSite.site_id,
        camera_id: camera.camera_id,
        source_type: sourceType,
        rtsp_url: sourceType === 'rtsp' ? rtspUrl : undefined,
      });

      setActive(true);
      if (sourceType !== 'rtsp') {
        stopCaptureLoop();
        runningRef.current = true;
        void runLoop();
      }
    } catch (err) {
      setCaptureError(
        err instanceof Error ? err.message : 'Could not start the selected camera source.',
      );
    } finally {
      setStarting(false);
    }
  }

  const peopleCount = status?.people_count ?? 0;
  const vehicleCount = status?.vehicle_count ?? 0;
  const activeHazards = status?.active_hazards ?? 0;
  const reportsFiled = status?.auto_reports_filed ?? 0;

  const threatLevel = Math.max(
    signals.fire_score,
    signals.smoke_score,
    signals.visibility_drop,
    activeHazards > 0 ? 0.55 : 0,
  );
  const alarmed = signals.fire_active || signals.smoke_active || Boolean(alarm);

  return (
    <div className="space-y-4">
      {/* ------------------------------------------------------------ HEADER */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <PulseDot tone={active ? 'critical' : 'hivis'} size={7} live={active} />
            <span className="font-mono text-2xs tracked text-ink-4">
              CCTV HAZARD MONITORING · {selectedSite.canonical_name.toUpperCase()}
            </span>
          </div>
          <h1 className="mt-1.5 font-display text-5xl text-ink">
            Camera <span className="text-hivis">Watch</span>
          </h1>
          <p className="mt-1.5 max-w-2xl text-sm text-ink-3">
            Fire, smoke, obscuration, falls, falling masses and zone breaches, detected live from a
            camera feed or an uploaded video. Anything it sees is filed as a complaint through the
            SIF pipeline and given a response priority — automatically.
          </p>
        </div>
        <Hint content="Demo camera footage — a browser webcam or a video you upload, never a live OIL India feed.">
          <div className="flex items-center gap-2 rounded-md border border-medium-edge bg-medium-wash px-3 py-2">
            <AlertTriangle className="h-3.5 w-3.5 text-medium" strokeWidth={2.2} />
            <span className="font-mono text-2xs tracked text-medium">DEMO CAMERA FEED</span>
          </div>
        </Hint>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1.45fr_1fr]">
        {/* -------------------------------------------------------------- LEFT */}
        <div className="space-y-3">
          <ScanPanel className="flex flex-col" active={active}>
            <PanelHead
              title="CAMERA FEED"
              sub={camera ? `${camera.camera_name} · ${camera.camera_id}` : 'Select a camera'}
              tone={alarmed ? 'critical' : active ? 'hivis' : 'neutral'}
              right={
                camerasLoading ? (
                  <Chip tone="neutral">LOADING CAMERAS…</Chip>
                ) : (
                  <select
                    value={cameraId}
                    onChange={(e) => setCameraId(e.target.value)}
                    className="rounded-sm border border-line-bright bg-surface-2 px-2 py-1 font-mono text-2xs tracked text-ink outline-none"
                  >
                    {cameras.map((c) => (
                      <option key={c.camera_id} value={c.camera_id}>
                        {c.camera_id}
                      </option>
                    ))}
                  </select>
                )
              }
            />

            {camerasError ? (
              <QueryError error={camerasError} compact />
            ) : (
              <div
                className={cn(
                  'relative aspect-video w-full overflow-hidden bg-void transition-shadow',
                  alarmed && 'ring-2 ring-critical',
                )}
              >
                <video ref={videoRef} muted playsInline className="h-full w-full object-contain" />
                <canvas
                  ref={overlayRef}
                  className="pointer-events-none absolute inset-0 h-full w-full"
                />
                <canvas ref={captureRef} className="hidden" />

                {!active && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-void/85 px-6 text-center">
                    <Video className="h-8 w-8 text-ink-4" strokeWidth={1.5} />
                    <div className="font-mono text-2xs tracked text-ink-3">
                      {sourceType === 'webcam'
                        ? 'Press Start to request webcam access.'
                        : sourceType === 'demo_video'
                          ? videoFileName
                            ? `${videoFileName} ready — press Start to analyse.`
                            : 'Upload a video file below, then press Start.'
                          : 'Enter an RTSP URL below, then press Start.'}
                    </div>
                    <p className="max-w-sm text-xs text-ink-4">
                      Nothing is simulated. No detection, hazard index, event or filed report
                      appears anywhere on this page until a real frame has been analysed.
                    </p>
                  </div>
                )}

                {/* Running-state chrome, drawn over the picture */}
                <div className="absolute left-2 top-2 flex items-center gap-1.5 rounded-sm bg-void/70 px-2 py-1 backdrop-blur-sm">
                  <PulseDot tone={active ? 'critical' : 'neutral'} size={6} live={active} />
                  <span className="font-mono text-2xs tracked text-ink-2">
                    {active ? 'ANALYSING' : 'IDLE'}
                  </span>
                  {active && (
                    <span className="font-mono text-2xs tabular text-ink-4">
                      · {latency.toFixed(0)}ms · f{signals.frame_index}
                    </span>
                  )}
                </div>
                {status && (
                  <div className="absolute right-2 top-2 rounded-sm bg-void/70 px-2 py-1 font-mono text-2xs tracked text-ink-3 backdrop-blur-sm">
                    {status.model_name.toUpperCase()} · {status.device.toUpperCase()}
                  </div>
                )}

                {/* Alarm banner — the one moment this page shouts */}
                <AnimatePresence>
                  {alarm && (
                    <motion.div
                      initial={{ y: 40, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      exit={{ y: 40, opacity: 0 }}
                      transition={{ type: 'spring', stiffness: 320, damping: 26 }}
                      className="absolute inset-x-0 bottom-0 flex flex-wrap items-center gap-2 border-t border-critical-edge bg-critical-wash/95 px-3 py-2 backdrop-blur-sm"
                    >
                      <AlertTriangle className="h-4 w-4 shrink-0 text-critical" strokeWidth={2.4} />
                      <span className="font-mono text-2xs tracked text-critical">
                        {(VISION_EVENT_LABEL[alarm.event_type] ?? alarm.event_type).toUpperCase()}
                      </span>
                      <span className="truncate text-xs text-ink-2">{alarm.observed}</span>
                      {alarm.auto_report_id && (
                        <Link
                          to={`/reports/${alarm.auto_report_id}`}
                          className="ml-auto flex items-center gap-1 rounded-sm border border-critical-edge px-2 py-0.5 font-mono text-2xs tracked text-critical hover:bg-critical/10"
                        >
                          <FileText className="h-3 w-3" strokeWidth={2} />
                          {alarm.auto_report_priority} FILED
                        </Link>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}

            {status && !status.model_ready && (
              <div className="flex items-start gap-2 border-t border-line px-4 py-2 text-critical">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" strokeWidth={2} />
                <span className="text-xs">
                  Detection model unavailable: {status.model_error ?? 'unknown error'}. Bounding
                  boxes stay empty until the backend can load the weights — the scene analysers
                  (fire, smoke, visibility) still run.
                </span>
              </div>
            )}

            {captureError && (
              <div className="flex items-center gap-2 border-t border-line px-4 py-2 text-critical">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
                <span className="text-xs">{captureError}</span>
              </div>
            )}

            {/* ------------------------------------------------ source controls */}
            <div className="space-y-3 border-t border-line px-4 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-2xs tracked text-ink-4">SOURCE</span>
                {(
                  [
                    { key: 'demo_video', label: 'Upload Video', icon: Film },
                    { key: 'webcam', label: 'Live Webcam', icon: Webcam },
                    { key: 'rtsp', label: 'RTSP / NVR', icon: Radio },
                  ] as { key: VisionSourceType; label: string; icon: typeof Webcam }[]
                ).map(({ key, label, icon: Icon }) => (
                  <button
                    key={key}
                    type="button"
                    disabled={active}
                    onClick={() => setSourceType(key)}
                    className={cn(
                      'flex items-center gap-1.5 rounded-sm border px-2.5 py-1.5 font-mono text-2xs tracked transition-colors disabled:cursor-not-allowed disabled:opacity-40',
                      sourceType === key
                        ? 'border-hivis-edge bg-hivis-wash text-hivis'
                        : 'border-line-bright text-ink-2 hover:text-ink',
                    )}
                  >
                    <Icon className="h-3 w-3" strokeWidth={2} />
                    {label}
                  </button>
                ))}

                <div className="ml-auto flex items-center gap-2">
                  {!active ? (
                    <button
                      type="button"
                      onClick={handleStart}
                      disabled={
                        starting ||
                        !camera ||
                        (sourceType === 'demo_video' && !videoObjectUrl) ||
                        (sourceType === 'rtsp' && !rtspUrl)
                      }
                      className="flex items-center gap-1.5 rounded-md bg-hivis px-3 py-1.5 font-mono text-2xs tracked text-on-hivis transition-transform hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      {starting ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={2.4} />
                      ) : (
                        <CameraIcon className="h-3.5 w-3.5" strokeWidth={2.4} />
                      )}
                      START
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={handleStop}
                      className="flex items-center gap-1.5 rounded-md border border-critical-edge bg-critical-wash px-3 py-1.5 font-mono text-2xs tracked text-critical transition-transform hover:scale-[1.02]"
                    >
                      STOP
                    </button>
                  )}
                </div>
              </div>

              {sourceType === 'demo_video' && (
                <label className="flex w-fit cursor-pointer items-center gap-2 rounded-sm border border-line-bright px-2.5 py-1.5 text-ink-2 hover:text-hivis">
                  <Upload className="h-3.5 w-3.5" strokeWidth={2} />
                  <span className="font-mono text-2xs tracked">
                    {videoFileName ?? 'CHOOSE A VIDEO FILE'}
                  </span>
                  <input
                    type="file"
                    accept="video/*"
                    className="hidden"
                    disabled={active}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleFileSelected(file);
                    }}
                  />
                </label>
              )}

              {sourceType === 'rtsp' && (
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={rtspUrl}
                    onChange={(e) => setRtspUrl(e.target.value)}
                    disabled={active}
                    placeholder="rtsp://user:pass@camera-host/stream"
                    className="w-full max-w-md rounded-sm border border-line-bright bg-surface-2 px-2.5 py-1.5 font-mono text-2xs text-ink outline-none placeholder:text-ink-4"
                  />
                  <HelpDot content="Connects the backend directly to an IP camera or NVR. Frames are then read and analysed server-side, so this page shows the resulting events rather than the picture." />
                </div>
              )}
            </div>
          </ScanPanel>

          {/* ----------------------------------------------- live hazard indices */}
          <ScanPanel active={active}>
            <PanelHead
              title="LIVE HAZARD INDICES"
              sub="Per-frame scene analysis — these move before anything fires"
              tone={alarmed ? 'critical' : 'hivis'}
              right={
                <Chip tone={threatLevel > 0.6 ? 'critical' : threatLevel > 0.25 ? 'high' : 'low'} dot>
                  THREAT {(threatLevel * 100).toFixed(0)}%
                </Chip>
              }
            />
            <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2">
              <SignalMeter
                icon={Flame}
                label="FIRE INDEX"
                value={signals.fire_score}
                triggered={signals.fire_active}
                tone="critical"
                hint="Flame-coloured pixels that also flicker frame to frame. A static orange object scores near zero."
              />
              <SignalMeter
                icon={Wind}
                label="SMOKE INDEX"
                value={signals.smoke_score}
                triggered={signals.smoke_active}
                tone="high"
                hint="Desaturated moving regions with lower edge energy than the scene. People and vehicles are masked out first."
              />
              <SignalMeter
                icon={AlertTriangle}
                label="VISIBILITY LOSS"
                value={signals.visibility_drop}
                triggered={signals.visibility_active}
                tone="medium"
                hint="How far scene detail has fallen below this camera's own rolling baseline — dust, gas or a smoke layer."
              />
              <SignalMeter
                icon={PersonStanding}
                label="SCENE MOTION"
                value={signals.motion_score}
                triggered={false}
                tone="info"
                hint="Fraction of the frame currently moving. Context for the other indices, not an alarm on its own."
              />
            </div>
            <div className="grid grid-cols-2 gap-3 border-t border-line px-4 py-3 sm:grid-cols-4">
              {[
                { label: 'PEOPLE', value: peopleCount, tone: 'hivis' as const },
                { label: 'VEHICLES', value: vehicleCount, tone: 'info' as const },
                { label: 'ACTIVE HAZARDS', value: activeHazards, tone: 'critical' as const },
                { label: 'REPORTS FILED', value: reportsFiled, tone: 'violet' as const },
              ].map((tile) => (
                <div key={tile.label}>
                  <div className="font-mono text-2xs tracked text-ink-4">{tile.label}</div>
                  <div
                    className={cn(
                      'mt-0.5 font-display text-3xl',
                      tile.tone === 'critical'
                        ? 'text-critical'
                        : tile.tone === 'info'
                          ? 'text-info'
                          : tile.tone === 'violet'
                            ? 'text-violet'
                            : 'text-hivis',
                    )}
                  >
                    <Counter value={tile.value} />
                  </div>
                </div>
              ))}
            </div>
            {lastDetections.length > 0 && (
              <div className="flex flex-wrap gap-1.5 border-t border-line px-4 py-2.5">
                {lastDetections.slice(0, 12).map((d, i) => (
                  <Chip key={i} tone={d.class_name === 'person' ? 'hivis' : 'info'}>
                    {d.class_name} {(d.confidence * 100).toFixed(0)}%
                  </Chip>
                ))}
              </div>
            )}
          </ScanPanel>
        </div>

        {/* ------------------------------------------------------------- RIGHT */}
        <div className="space-y-3">
          {/* Auto-filed complaints */}
          <ScanPanel active={active}>
            <PanelHead
              title="AUTO-FILED COMPLAINTS"
              sub="Every hazard raises a report — priority set by camera + SIF pipeline"
              tone="violet"
              right={
                autoReports.isFetching ? (
                  <Chip tone="neutral">FILING…</Chip>
                ) : (
                  <Chip tone="violet" dot>
                    {autoReports.data?.total ?? 0} TOTAL
                  </Chip>
                )
              }
            />
            <div className="max-h-52 overflow-y-auto">
              {filedReports.length === 0 ? (
                <EmptyPanel
                  title="No complaints filed yet"
                  message="A detected hazard writes its own report here, then routes it for review."
                />
              ) : (
                <LiveFeed
                  items={filedReports}
                  max={12}
                  keyFor={(r) => r.report_id}
                  renderItem={(r) => (
                    <Link
                      to={`/reports/${r.report_id}`}
                      className="flex items-center gap-2 px-4 py-2 transition-colors hover:bg-surface-2"
                    >
                      <Chip
                        tone={VISION_PRIORITY_TONE[(r.priority as 'P1') ?? 'P4'] ?? 'low'}
                        dot
                      >
                        {r.priority ?? 'P4'}
                      </Chip>
                      <span className="truncate text-xs text-ink">{r.lsr_tag}</span>
                      <span className="ml-auto shrink-0 font-mono text-2xs tabular text-ink-4">
                        {new Date(r.timestamp).toLocaleTimeString()}
                      </span>
                    </Link>
                  )}
                />
              )}
            </div>
          </ScanPanel>

          {/* Event feed */}
          <ScanPanel className="flex h-[300px] flex-col" active={active}>
            <PanelHead
              title="HAZARD EVENTS"
              sub="Fire · smoke · falls · falling masses · zones · vehicles"
              tone="critical"
              right={
                eventsQuery.isFetching ? (
                  <Chip tone="neutral">SYNCING…</Chip>
                ) : (
                  <Chip tone={activeHazards > 0 ? 'critical' : 'low'} dot>
                    {activeHazards} ACTIVE
                  </Chip>
                )
              }
            />
            <div className="min-h-0 flex-1 overflow-y-auto">
              {eventsQuery.error ? (
                <QueryError error={eventsQuery.error} compact />
              ) : events.length === 0 ? (
                <EmptyPanel
                  title="No hazard events yet"
                  message="Start a source. Fire, smoke, a fall or a falling mass will appear here within a second or two of happening."
                />
              ) : (
                <LiveFeed
                  items={events}
                  max={30}
                  keyFor={(e) => e.event_id}
                  renderItem={(e) => (
                    <button
                      type="button"
                      onClick={() => setSelectedEvent(e)}
                      className={cn(
                        'block w-full px-4 py-2.5 text-left transition-colors hover:bg-surface-2',
                        e.status === 'acknowledged' && 'opacity-60',
                        selectedEvent?.event_id === e.event_id && 'bg-surface-2',
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <Chip tone={VISION_SEVERITY_TONE[e.severity]} dot>
                          {e.severity.toUpperCase()}
                        </Chip>
                        <span className="truncate text-xs text-ink">
                          {VISION_EVENT_LABEL[e.event_type] ?? e.event_type.replace(/_/g, ' ')}
                        </span>
                        <span className="ml-auto shrink-0 font-mono text-2xs tabular text-ink-4">
                          {new Date(e.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-2xs text-ink-3">
                        <span>{(e.confidence * 100).toFixed(0)}% confidence</span>
                        {e.auto_report_priority && (
                          <>
                            <span>·</span>
                            <span className="text-violet">
                              filed {e.auto_report_priority}
                            </span>
                          </>
                        )}
                        {e.status === 'acknowledged' && (
                          <span className="ml-auto flex items-center gap-1 text-low">
                            <CheckCircle2 className="h-3 w-3" /> acknowledged
                          </span>
                        )}
                      </div>
                    </button>
                  )}
                />
              )}
            </div>
          </ScanPanel>

          {/* Event detail */}
          <ScanPanel>
            <PanelHead title="EVENT DETAIL" sub="Observation, interpretation, and what was filed" />
            {!selectedEvent ? (
              <EmptyPanel title="Select an event" message="Click any event above to see its detail." />
            ) : (
              <div className="space-y-3 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <Chip tone={VISION_SEVERITY_TONE[selectedEvent.severity]} dot>
                      {selectedEvent.severity.toUpperCase()}
                    </Chip>
                    <Chip tone="neutral">
                      {VISION_EVENT_LABEL[selectedEvent.event_type] ?? selectedEvent.event_type}
                    </Chip>
                  </div>
                  {selectedEvent.status === 'active' ? (
                    <button
                      type="button"
                      onClick={() =>
                        acknowledge.mutate(selectedEvent.event_id, {
                          onSuccess: (updated) => setSelectedEvent(updated),
                        })
                      }
                      disabled={acknowledge.isPending}
                      className="flex items-center gap-1.5 rounded-sm border border-line-bright px-2 py-1 font-mono text-2xs tracked text-ink-2 hover:border-hivis-edge hover:text-hivis disabled:opacity-50"
                    >
                      <CheckCircle2 className="h-3 w-3" strokeWidth={2} />
                      ACKNOWLEDGE
                    </button>
                  ) : (
                    <span className="font-mono text-2xs tracked text-low">ACKNOWLEDGED</span>
                  )}
                </div>

                {/* The filed complaint — the point of the whole feature */}
                {selectedEvent.auto_report_id ? (
                  <Link
                    to={`/reports/${selectedEvent.auto_report_id}`}
                    className="flex items-center gap-2 rounded-md border border-violet/40 bg-violet-wash px-3 py-2 transition-colors hover:bg-violet/15"
                  >
                    <FileText className="h-3.5 w-3.5 shrink-0 text-violet" strokeWidth={2.2} />
                    <div className="min-w-0">
                      <div className="font-mono text-2xs tracked text-violet">
                        COMPLAINT {selectedEvent.auto_report_id} ·{' '}
                        {selectedEvent.auto_report_priority} —{' '}
                        {selectedEvent.auto_report_priority_label}
                      </div>
                      <div className="mt-0.5 text-2xs text-ink-3">
                        Filed automatically · {selectedEvent.auto_report_bucket} ·{' '}
                        {selectedEvent.auto_report_sif ? 'SIF potential' : 'no SIF potential'} —
                        open the full analysis
                      </div>
                    </div>
                  </Link>
                ) : (
                  <div className="rounded-md border border-critical-edge bg-critical-wash px-3 py-2 text-2xs text-critical">
                    No complaint could be filed for this event
                    {selectedEvent.auto_report_error
                      ? `: ${selectedEvent.auto_report_error}`
                      : '.'}{' '}
                    The event itself is still recorded.
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2 font-mono text-2xs tracked text-ink-4">
                  <span>SITE: {selectedEvent.site_id}</span>
                  <span>CAMERA: {selectedEvent.camera_name}</span>
                  <span>ZONE: {selectedEvent.roi ?? '—'}</span>
                  <span>CONFIDENCE: {(selectedEvent.confidence * 100).toFixed(0)}%</span>
                </div>

                <div>
                  <div className="font-mono text-2xs tracked text-ink-4">OBSERVED</div>
                  <p className="mt-1 text-sm text-ink">{selectedEvent.observed}</p>
                </div>
                <div>
                  <div className="font-mono text-2xs tracked text-ink-4">SAFETY INTERPRETATION</div>
                  <p className="mt-1 text-sm text-ink-2">{selectedEvent.inference}</p>
                </div>
                <div>
                  <div className="font-mono text-2xs tracked text-ink-4">SIF RELEVANCE</div>
                  <p className="mt-1 text-sm text-ink-2">{selectedEvent.sif_relevance}</p>
                </div>
                <div>
                  <div className="font-mono text-2xs tracked text-ink-4">
                    RELATED LIFE-SAVING RULE
                  </div>
                  <p className="mt-1">
                    <Chip tone="violet">{selectedEvent.lsr_tag}</Chip>
                  </p>
                </div>
                <div className="border-t border-line pt-2">
                  <div className="font-mono text-2xs tracked text-ink-4">DETECTOR EVIDENCE</div>
                  <p className="mt-1 font-mono text-2xs text-ink-3">{selectedEvent.evidence}</p>
                </div>
              </div>
            )}
          </ScanPanel>
        </div>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="rounded-md border border-line-faint bg-surface-2/60 px-4 py-2 text-2xs text-ink-4"
      >
        Camera Watch is decision support, not autonomous safety control. It is tuned to over-report
        rather than miss: a false alarm costs a dismissed report, a missed one does not. PPE
        (helmet/vest) detection is not enabled — the pretrained detector used here does not
        recognise PPE, and this page does not claim it does.
      </motion.div>
    </div>
  );
}

/* ========================================================================== */

/**
 * One live hazard index.
 *
 * The bar is the fast-moving part and the number underneath is the precise
 * one; the border and icon light up only once the analyser has actually
 * triggered, so a rising index and a fired alarm never look the same.
 */
function SignalMeter({
  icon: Icon,
  label,
  value,
  triggered,
  tone,
  hint,
}: {
  icon: typeof Flame;
  label: string;
  value: number;
  triggered: boolean;
  tone: 'critical' | 'high' | 'medium' | 'info';
  hint: string;
}) {
  const pct = Math.max(0, Math.min(1, value || 0));
  return (
    <Hint content={hint}>
      <div
        className={cn(
          'rounded-md border px-3 py-2.5 transition-colors',
          triggered ? 'border-critical-edge bg-critical-wash' : 'border-line',
        )}
      >
        <div className="flex items-center gap-1.5">
          <motion.span
            animate={triggered ? { scale: [1, 1.18, 1] } : { scale: 1 }}
            transition={{ repeat: triggered ? Infinity : 0, duration: 1.1 }}
            className="flex"
          >
            <Icon
              className={cn('h-3.5 w-3.5', triggered ? 'text-critical' : 'text-ink-4')}
              strokeWidth={2.2}
            />
          </motion.span>
          <span className="font-mono text-2xs tracked text-ink-4">{label}</span>
          {triggered && (
            <span className="ml-auto font-mono text-2xs tracked text-critical">TRIGGERED</span>
          )}
        </div>
        <div className="mt-2 flex items-center gap-2">
          <Bar
            value={pct}
            tone={triggered ? 'critical' : tone}
            height={5}
            duration={0.25}
            className="flex-1"
          />
          <span className="w-9 shrink-0 text-right font-mono text-2xs tabular text-ink-2">
            {(pct * 100).toFixed(0)}%
          </span>
        </div>
      </div>
    </Hint>
  );
}
