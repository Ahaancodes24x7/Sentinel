import { useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  Camera as CameraIcon,
  CheckCircle2,
  Film,
  Loader2,
  Radio,
  Upload,
  Video,
  Webcam,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '../lib/cn';
import { useSelectedSite } from '../lib/siteContext';
import { api } from '../api/client';
import {
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
  VisionSafetyEvent,
  VisionSourceType,
} from '../api/types';
import { VISION_SEVERITY_TONE } from '../api/types';
import { Chip, Counter, LiveFeed, PanelHead, PulseDot, ScanPanel } from '../components/kinetic';
import { Hint, HelpDot } from '../components/common/Hint';
import { EmptyPanel, QueryError } from '../components/common/QueryState';

const ANALYZE_INTERVAL_MS = 700;
const CAPTURE_WIDTH = 640;

/* --------------------------------------------------------------------------
 * Everything shown here — the video, the boxes, the events on the right —
 * comes from a real request/response round trip with the backend's YOLO
 * detector and hazard-rule engine. There is no timer that fabricates a count
 * or an event; if the analyze loop stops, the numbers stop moving.
 * ----------------------------------------------------------------------- */

function roiStrokeColor(roiType: string): string {
  if (roiType === 'restricted_zone') return 'rgba(239,68,68,0.95)';
  if (roiType === 'lifting_zone') return 'rgba(245,158,11,0.95)';
  return 'rgba(56,189,248,0.85)';
}

export function LiveVisionPage() {
  const { selectedSite } = useSelectedSite();

  const { data: camerasData, isLoading: camerasLoading, error: camerasError } = useVisionCameras(
    selectedSite.site_id,
  );
  const cameras = camerasData?.cameras ?? [];
  const [cameraId, setCameraId] = useState<string>('');

  useEffect(() => {
    if (cameras.length && !cameras.some((c) => c.camera_id === cameraId)) {
      setCameraId(cameras[0].camera_id);
    }
  }, [cameras, cameraId]);

  const camera = cameras.find((c) => c.camera_id === cameraId);

  const [sourceType, setSourceType] = useState<VisionSourceType>('webcam');
  const [rtspUrl, setRtspUrl] = useState('');
  const [videoObjectUrl, setVideoObjectUrl] = useState<string | null>(null);
  const [videoFileName, setVideoFileName] = useState<string | null>(null);
  const [active, setActive] = useState(false);
  const [starting, setStarting] = useState(false);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [lastDetections, setLastDetections] = useState<VisionDetectedObject[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<VisionSafetyEvent | null>(null);
  const [flashHigh, setFlashHigh] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const captureRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<number | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  const startMutation = useVisionStart();
  const stopMutation = useVisionStop();
  const acknowledge = useVisionAcknowledge();
  const statusQuery = useVisionStatus(cameraId, Boolean(cameraId));
  const eventsQuery = useVisionEvents(cameraId, 40, Boolean(cameraId));

  const status = statusQuery.data;
  const events = eventsQuery.data?.events ?? [];

  // Switching site or camera ends whatever session was running — starting a
  // feed for the wrong camera would be worse than requiring a fresh Start.
  useEffect(() => {
    handleStop();
    setSelectedEvent(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameraId, selectedSite.site_id]);

  useEffect(() => {
    return () => {
      stopCaptureLoop();
      streamRef.current?.getTracks().forEach((t) => t.stop());
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function stopCaptureLoop() {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }

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
      if (sourceType === 'webcam') {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480 },
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
      } else if (sourceType === 'demo_video') {
        if (!videoObjectUrl || !videoRef.current) {
          setCaptureError('Select a demo video file first.');
          setStarting(false);
          return;
        }
        videoRef.current.srcObject = null;
        videoRef.current.src = videoObjectUrl;
        videoRef.current.loop = true;
        await videoRef.current.play();
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
        intervalRef.current = window.setInterval(captureAndAnalyze, ANALYZE_INTERVAL_MS);
      }
    } catch (err) {
      setCaptureError(err instanceof Error ? err.message : 'Could not start the camera source.');
    } finally {
      setStarting(false);
    }
  }

  function handleStop() {
    setActive(false);
    stopCaptureLoop();
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.pause();
    }
    if (cameraId) stopMutation.mutate({ camera_id: cameraId });
    const canvas = overlayRef.current;
    canvas?.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height);
    setLastDetections([]);
  }

  async function captureAndAnalyze() {
    const video = videoRef.current;
    const capture = captureRef.current;
    if (!video || !capture || video.readyState < 2 || !video.videoWidth) return;

    const targetW = CAPTURE_WIDTH;
    const targetH = Math.round(targetW * (video.videoHeight / video.videoWidth));
    capture.width = targetW;
    capture.height = targetH;
    const ctx = capture.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, targetW, targetH);
    const dataUrl = capture.toDataURL('image/jpeg', 0.6);

    try {
      const res = await api.post<VisionAnalyzeFrameResponse>('/vision/analyze-frame', {
        site_id: selectedSite.site_id,
        camera_id: cameraId,
        image_base64: dataUrl,
      });
      if (res.skipped) return;
      setLastDetections(res.detections);
      drawOverlay(res.detections);
      if (res.new_events.some((e) => e.severity === 'high')) {
        setFlashHigh(true);
        window.setTimeout(() => setFlashHigh(false), 1600);
      }
      if (res.new_events.length) {
        eventsQuery.refetch();
        statusQuery.refetch();
      }
    } catch {
      // Transient network hiccup — the next tick tries again. A single
      // failed frame must not stop the loop or show a fake state.
    }
  }

  function drawOverlay(detections: VisionDetectedObject[]) {
    const canvas = overlayRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;
    const w = video.clientWidth || 640;
    const h = video.clientHeight || 360;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, w, h);

    (camera?.rois ?? []).forEach((roi) => {
      const color = roiStrokeColor(roi.roi_type);
      ctx.beginPath();
      roi.points.forEach(([x, y], i) => {
        const px = x * w;
        const py = y * h;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.closePath();
      ctx.setLineDash([6, 4]);
      ctx.lineWidth = 2;
      ctx.strokeStyle = color;
      ctx.stroke();
      ctx.fillStyle = color.replace(/0\.\d+\)/, '0.08)');
      ctx.fill();
      ctx.setLineDash([]);
      ctx.font = '11px monospace';
      ctx.fillStyle = color;
      const [lx, ly] = roi.points[0];
      ctx.fillText(roi.name, lx * w + 4, ly * h + 12);
    });

    detections.forEach((d) => {
      const [x1, y1, x2, y2] = d.bbox;
      const px = x1 * w;
      const py = y1 * h;
      const pw = (x2 - x1) * w;
      const ph = (y2 - y1) * h;
      const color = d.class_name === 'person' ? '#d4ff3f' : '#38bdf8';
      ctx.lineWidth = 2;
      ctx.strokeStyle = color;
      ctx.strokeRect(px, py, pw, ph);
      const label = `${d.class_name} ${(d.confidence * 100).toFixed(0)}%`;
      ctx.font = '11px monospace';
      const textW = ctx.measureText(label).width + 6;
      ctx.fillStyle = color;
      ctx.fillRect(px, Math.max(0, py - 14), textW, 14);
      ctx.fillStyle = '#0a0a0a';
      ctx.fillText(label, px + 3, Math.max(10, py - 3));
    });
  }

  const peopleCount = status?.people_count ?? 0;
  const vehicleCount = status?.vehicle_count ?? 0;
  const activeHazards = status?.active_hazards ?? 0;
  const highPriority = status?.high_priority_hazards ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <PulseDot tone={active ? 'critical' : 'hivis'} size={7} live={active} />
            <span className="font-mono text-2xs tracked text-ink-4">
              LIVE SAFETY VISION · {selectedSite.canonical_name.toUpperCase()}
            </span>
          </div>
          <h1 className="mt-1.5 font-display text-5xl text-ink">
            Camera <span className="text-hivis">Watch</span>
          </h1>
          <p className="mt-1.5 max-w-2xl text-sm text-ink-3">
            Real-time YOLO object detection over a webcam or a demo video, checked against
            configurable safety zones. Detections and events below come from the live model —
            nothing here is simulated.
          </p>
        </div>
        <Hint content="Demo camera footage — a browser webcam or an uploaded/local video, never a live OIL India feed.">
          <div className="flex items-center gap-2 rounded-md border border-medium-edge bg-medium-wash px-3 py-2">
            <AlertTriangle className="h-3.5 w-3.5 text-medium" strokeWidth={2.2} />
            <span className="font-mono text-2xs tracked text-medium">DEMO CAMERA FEED</span>
          </div>
        </Hint>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1.4fr_1fr]">
        {/* ---------------------------------------------------------------- LEFT */}
        <div className="space-y-3">
          <ScanPanel className="flex flex-col" active={active}>
            <PanelHead
              title="CAMERA FEED"
              sub={camera ? `${camera.camera_name} · ${camera.camera_id}` : 'Select a camera'}
              tone={active ? 'critical' : 'hivis'}
              right={
                <div className="flex items-center gap-1.5">
                  {camerasLoading ? (
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
                  )}
                </div>
              }
            />

            {camerasError ? (
              <QueryError error={camerasError} compact />
            ) : (
              <div
                className={cn(
                  'relative aspect-video w-full overflow-hidden bg-void',
                  flashHigh && 'ring-2 ring-critical',
                )}
              >
                <video
                  ref={videoRef}
                  muted
                  playsInline
                  className="h-full w-full object-contain"
                />
                <canvas ref={overlayRef} className="pointer-events-none absolute inset-0 h-full w-full" />
                <canvas ref={captureRef} className="hidden" />

                {!active && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-void/85 text-center">
                    <Video className="h-8 w-8 text-ink-4" strokeWidth={1.5} />
                    <div className="font-mono text-2xs tracked text-ink-3">
                      {sourceType === 'webcam'
                        ? 'Select "Start" to request webcam access.'
                        : sourceType === 'demo_video'
                          ? videoFileName
                            ? `${videoFileName} ready — press Start to analyze.`
                            : 'Choose a demo video file below, then press Start.'
                          : 'Enter an RTSP URL below, then press Start.'}
                    </div>
                    <p className="max-w-xs text-xs text-ink-4">
                      No fake detections are shown here. Nothing appears in the panels on the
                      right until a real video source is analyzed.
                    </p>
                  </div>
                )}

                <div className="absolute left-2 top-2 flex items-center gap-1.5 rounded-sm bg-void/70 px-2 py-1">
                  <PulseDot tone={active ? 'critical' : 'neutral'} size={6} live={active} />
                  <span className="font-mono text-2xs tracked text-ink-2">
                    {active ? 'ANALYZING' : 'IDLE'}
                  </span>
                </div>
                {status && (
                  <div className="absolute right-2 top-2 rounded-sm bg-void/70 px-2 py-1 font-mono text-2xs tracked text-ink-3">
                    {status.model_name.toUpperCase()} · {status.device.toUpperCase()}
                  </div>
                )}
              </div>
            )}

            {status && !status.model_ready && (
              <div className="flex items-center gap-2 border-t border-line px-4 py-2 text-critical">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
                <span className="text-xs">
                  Vision model unavailable: {status.model_error ?? 'unknown error'}. Bounding boxes
                  will stay empty until the backend can load YOLO weights.
                </span>
              </div>
            )}

            {captureError && (
              <div className="flex items-center gap-2 border-t border-line px-4 py-2 text-critical">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
                <span className="text-xs">{captureError}</span>
              </div>
            )}

            {/* Source controls */}
            <div className="space-y-3 border-t border-line px-4 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-2xs tracked text-ink-4">SOURCE</span>
                {(
                  [
                    { key: 'webcam', label: 'Webcam', icon: Webcam },
                    { key: 'demo_video', label: 'Demo Video', icon: Film },
                    { key: 'rtsp', label: 'RTSP (optional)', icon: Radio },
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
                    {videoFileName ?? 'CHOOSE MP4 FILE'}
                  </span>
                  <input
                    type="file"
                    accept="video/mp4,video/*"
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
                  <HelpDot content="Optional and experimental — the demo does not depend on this working. Processed server-side by a background OpenCV capture thread." />
                </div>
              )}
            </div>
          </ScanPanel>

          {/* Current safety status */}
          <ScanPanel>
            <PanelHead title="CURRENT SAFETY STATUS" sub="Live counts from this camera's session" />
            <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-4">
              {[
                { label: 'PEOPLE DETECTED', value: peopleCount, tone: 'hivis' as const },
                { label: 'VEHICLES DETECTED', value: vehicleCount, tone: 'info' as const },
                { label: 'ACTIVE HAZARDS', value: activeHazards, tone: 'high' as const },
                { label: 'HIGH-PRIORITY HAZARDS', value: highPriority, tone: 'critical' as const },
              ].map((tile) => (
                <div key={tile.label} className="rounded-md border border-line px-3 py-2.5">
                  <div className="font-mono text-2xs tracked text-ink-4">{tile.label}</div>
                  <div
                    className={cn(
                      'mt-1 font-display text-3xl',
                      tile.tone === 'critical'
                        ? 'text-critical'
                        : tile.tone === 'high'
                          ? 'text-high'
                          : tile.tone === 'info'
                            ? 'text-info'
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
                {lastDetections.map((d, i) => (
                  <Chip key={i} tone={d.class_name === 'person' ? 'hivis' : 'info'}>
                    {d.class_name} {(d.confidence * 100).toFixed(0)}%
                  </Chip>
                ))}
              </div>
            )}
          </ScanPanel>
        </div>

        {/* ---------------------------------------------------------------- RIGHT */}
        <div className="space-y-3">
          <ScanPanel className="flex h-[420px] flex-col">
            <PanelHead
              title="LIVE SAFETY EVENTS"
              sub="Restricted zone, lifting zone, vehicle-person proximity"
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
                  title="No safety events yet"
                  message="Start a camera source and let a person or vehicle enter a configured zone."
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
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <Chip tone={VISION_SEVERITY_TONE[e.severity]} dot>
                          {e.severity.toUpperCase()}
                        </Chip>
                        <span className="truncate text-xs text-ink">
                          {e.event_type.replace(/_/g, ' ')}
                        </span>
                        <span className="ml-auto font-mono text-2xs tabular text-ink-4">
                          {new Date(e.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center gap-2 text-2xs text-ink-3">
                        <span>{e.camera_name}</span>
                        <span>·</span>
                        <span>Confidence {(e.confidence * 100).toFixed(0)}%</span>
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
            <PanelHead title="EVENT DETAIL" sub="Observation vs. safety interpretation" />
            {!selectedEvent ? (
              <EmptyPanel title="Select an event" message="Click any event above to see its detail." />
            ) : (
              <div className="space-y-3 p-4">
                <div className="flex items-center justify-between">
                  <Chip tone={VISION_SEVERITY_TONE[selectedEvent.severity]} dot>
                    {selectedEvent.severity.toUpperCase()}
                  </Chip>
                  {selectedEvent.status === 'active' ? (
                    <button
                      type="button"
                      onClick={() => {
                        acknowledge.mutate(selectedEvent.event_id, {
                          onSuccess: (updated) => setSelectedEvent(updated),
                        });
                      }}
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

                <div className="grid grid-cols-2 gap-2 font-mono text-2xs tracked text-ink-4">
                  <span>SITE: {selectedEvent.site_id}</span>
                  <span>CAMERA: {selectedEvent.camera_name}</span>
                  <span>ROI: {selectedEvent.roi ?? '—'}</span>
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
                  <div className="font-mono text-2xs tracked text-ink-4">EVIDENCE</div>
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
        Live Safety Vision is decision support, not autonomous safety control. PPE (helmet/vest)
        detection is not enabled — the pretrained detector used for this demo does not recognize
        PPE, and this page does not claim it does.
      </motion.div>
    </div>
  );
}
