"""Sentinel Voice Bridge — collects spoken reports from the ESP32 voice node.

Runs on the laptop, which is a *client* on the node's access point. The loop is
deliberately boring:

    poll node /api/status  ->  new clip?  ->  GET /api/clip (WAV)
      ->  transcribe locally  ->  POST backend /api/v1/voice/ingest
      ->  POST node /api/result (verdict for the display)  ->  POST /api/ack

Two constraints shape every decision here, and both come from the node hosting
the WiFi rather than joining it:

1. **No internet.** While the laptop is joined to the node's AP it has no route
   out, so transcription must be a local model. faster-whisper is used; there is
   no hosted-ASR fallback because there is no network path to one.

2. **The node is the gateway**, so its address is the constant 192.168.4.1 while
   the laptop's own lease is not. That is why the laptop polls rather than the
   node pushing. See ../docs/protocol.md.

The backend runs on this same laptop, so it stays reachable on localhost
regardless of which network the WiFi adapter is attached to.

Usage
-----
    python sentinel_voice_bridge.py --site duliajan
    python sentinel_voice_bridge.py --dry-run --wav sample.wav    # no hardware
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

CAPTURES = Path(__file__).resolve().parent.parent / "captures"


# ---------------------------------------------------------------------------
# Speech to text
# ---------------------------------------------------------------------------
class Transcriber:
    """Wraps faster-whisper, loaded once.

    `small` is the default rather than `base`: site speech is code-mixed
    Assamese/Hindi/English against machinery noise, and `base` degrades on
    exactly the domain nouns that carry the safety meaning — "flange", "blowout
    preventer", "isolation". A misheard noun does not merely lower a score here,
    it changes which barrier the reasoning stage thinks was involved.
    """

    def __init__(self, model_size: str = "small", device: str = "auto", language: Optional[str] = None):
        self.model_size = model_size
        self.language = language
        self._model = None
        self._device = device

    def load(self) -> None:
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise SystemExit(
                "faster-whisper is not installed.\n"
                "    pip install -r requirements.txt\n"
                "Install it while you still have internet — once the laptop is "
                "joined to the node's access point there is no route out to "
                "download a model."
            ) from exc

        device = self._device
        compute = "int8"
        if device == "auto":
            try:
                import torch

                if torch.cuda.is_available():
                    device, compute = "cuda", "float16"
                else:
                    device = "cpu"
            except ImportError:
                device = "cpu"

        print(f"[stt] loading faster-whisper '{self.model_size}' on {device} ({compute})")
        self._model = WhisperModel(self.model_size, device=device, compute_type=compute)

    def transcribe(self, wav_path: Path) -> dict[str, Any]:
        self.load()
        segments, info = self._model.transcribe(
            str(wav_path),
            language=self.language,
            vad_filter=True,
            beam_size=5,
        )
        parts, probs = [], []
        for seg in segments:
            parts.append(seg.text.strip())
            # avg_logprob is a log probability; exp() puts it back on 0-1 so it
            # can be shown next to the pipeline's own confidence without a
            # reader having to know it was in log space.
            probs.append(pow(2.718281828, seg.avg_logprob))

        text = " ".join(p for p in parts if p).strip()
        confidence = round(sum(probs) / len(probs), 3) if probs else 0.0
        return {
            "text": text,
            "confidence": confidence,
            "language": getattr(info, "language", None),
            "duration": getattr(info, "duration", None),
            "model": f"faster-whisper-{self.model_size}",
        }


# ---------------------------------------------------------------------------
# Backend client
# ---------------------------------------------------------------------------
class SentinelClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token: Optional[str] = None

    def login(self) -> None:
        r = requests.post(
            f"{self.base}/api/v1/auth/login",
            json={"username": self.username, "password": self.password},
            timeout=10,
        )
        r.raise_for_status()
        self.token = r.json()["access_token"]
        print(f"[api] authenticated as {self.username}")

    def ingest_voice(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.token:
            self.login()
        r = requests.post(
            f"{self.base}/api/v1/voice/ingest",
            json=payload,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=60,
        )
        if r.status_code == 401:  # token rotated or backend restarted
            self.login()
            r = requests.post(
                f"{self.base}/api/v1/voice/ingest",
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=60,
            )
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# Node client
# ---------------------------------------------------------------------------
class VoiceNode:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")

    def status(self) -> Optional[dict[str, Any]]:
        try:
            r = requests.get(f"{self.base}/api/status", timeout=3)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            return None

    def fetch_clip(self, seq: int, dest: Path) -> Path:
        r = requests.get(f"{self.base}/api/clip", params={"seq": seq}, timeout=60, stream=True)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as fh:
            for chunk in r.iter_content(chunk_size=8192):
                fh.write(chunk)
        return dest

    def send_result(self, seq: int, verdict: dict[str, Any]) -> None:
        body = {
            "seq": seq,
            "bucket": verdict.get("bucket", ""),
            "sif_potential": bool(verdict.get("sif_potential", False)),
            "confidence": float(verdict.get("confidence", 0.0)),
            "lsr_tag": verdict.get("lsr_tag", ""),
            "report_id": verdict.get("report_id", ""),
        }
        try:
            requests.post(f"{self.base}/api/result", json=body, timeout=5)
        except requests.RequestException as exc:
            print(f"[node] could not return verdict to display: {exc}")

    def ack(self, seq: int) -> None:
        try:
            requests.post(f"{self.base}/api/ack", params={"seq": seq}, timeout=5)
        except requests.RequestException:
            pass


# ---------------------------------------------------------------------------
# The pipeline for one clip
# ---------------------------------------------------------------------------
def process_clip(
    wav_path: Path,
    seq: int,
    site: str,
    device_id: str,
    stt: Transcriber,
    api: SentinelClient,
    min_chars: int,
) -> Optional[dict[str, Any]]:
    print(f"[stt] transcribing {wav_path.name} ...")
    t0 = time.time()
    asr = stt.transcribe(wav_path)
    print(f'[stt] {time.time() - t0:.1f}s  conf={asr["confidence"]}  "{asr["text"]}"')

    # An empty or near-empty transcript is a recognition failure, not a report.
    # Filing it would put a blank row in front of a reviewer and let the node
    # claim a hazard was recorded when nothing intelligible was captured.
    if len(asr["text"]) < min_chars:
        print(f"[stt] transcript below {min_chars} chars - not filing")
        return None

    payload = {
        "site": site,
        "transcript": asr["text"],
        "device_id": device_id,
        "asr_confidence": asr["confidence"],
        "asr_model": asr["model"],
        "asr_language": asr["language"],
        "audio_seconds": asr["duration"],
        "clip_id": wav_path.name,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    verdict = api.ingest_voice(payload)
    print(
        f'[api] {verdict["report_id"]}  bucket={verdict["bucket"]}  '
        f'sif={verdict["sif_potential"]}  conf={verdict["confidence"]}  '
        f'lsr={verdict["lsr_tag"]}'
    )

    # Keep the transcript next to the audio. If a reviewer disputes a verdict,
    # the argument is almost always about what was actually said.
    wav_path.with_suffix(".json").write_text(
        json.dumps({"seq": seq, "asr": asr, "verdict": verdict}, indent=2),
        encoding="utf-8",
    )
    return verdict


def main() -> int:
    ap = argparse.ArgumentParser(description="Sentinel ESP32 voice-node bridge")
    ap.add_argument("--node", default="http://192.168.4.1", help="voice node base URL")
    ap.add_argument("--backend", default="http://127.0.0.1:8000", help="Sentinel API base URL")
    ap.add_argument("--site", default=None, help="override the site the node reports")
    ap.add_argument("--username", default="hse_demo")
    ap.add_argument("--password", default="demo123")
    ap.add_argument("--model", default="small", help="faster-whisper model size")
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    ap.add_argument("--language", default=None, help="force a language, e.g. en / hi / as")
    ap.add_argument("--poll", type=float, default=0.75, help="status poll interval, seconds")
    ap.add_argument("--min-chars", type=int, default=8, help="shortest transcript worth filing")
    ap.add_argument("--dry-run", action="store_true", help="process --wav once, no hardware")
    ap.add_argument("--wav", type=Path, help="WAV file to use with --dry-run")
    args = ap.parse_args()

    stt = Transcriber(args.model, args.device, args.language)
    api = SentinelClient(args.backend, args.username, args.password)

    # --dry-run exercises transcribe -> classify -> dashboard with no ESP32 on
    # the desk, so the workflow can be built and demonstrated before the
    # hardware is wired.
    if args.dry_run:
        if not args.wav or not args.wav.exists():
            print("--dry-run needs --wav <file.wav>", file=sys.stderr)
            return 2
        api.login()
        verdict = process_clip(
            args.wav, 0, args.site or "duliajan", "dry-run", stt, api, args.min_chars
        )
        return 0 if verdict else 1

    node = VoiceNode(args.node)
    api.login()
    print(f"[bridge] polling {args.node} every {args.poll}s  (Ctrl+C to stop)")

    last_seq = -1
    warned_offline = False

    while True:
        st = node.status()
        if st is None:
            if not warned_offline:
                print(f"[node] unreachable at {args.node} - is the laptop joined to its AP?")
                warned_offline = True
            time.sleep(2.0)
            continue

        if warned_offline:
            print(f'[node] back: {st.get("device_id")} fw={st.get("fw")} state={st.get("state")}')
            warned_offline = False

        seq = int(st.get("seq", 0))
        if st.get("clip_ready") and seq != last_seq:
            site = args.site or st.get("site") or "duliajan"
            device_id = st.get("device_id", "unknown")
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            dest = CAPTURES / f"{device_id}-{stamp}-seq{seq}.wav"

            try:
                print(f'\n[node] clip seq={seq} ({st.get("duration_s")}s) - collecting')
                node.fetch_clip(seq, dest)
                verdict = process_clip(dest, seq, site, device_id, stt, api, args.min_chars)
                if verdict:
                    node.send_result(seq, verdict)
                node.ack(seq)
                # Advanced only after a successful round trip, so a crash mid-way
                # leaves the clip on the node to be retried rather than lost.
                last_seq = seq
            except requests.RequestException as exc:
                print(f"[bridge] transfer failed, will retry: {exc}")
                time.sleep(2.0)

        time.sleep(args.poll)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[bridge] stopped")
