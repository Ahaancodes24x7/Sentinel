# Sentinel Voice Node — spoken hazard reporting

**SIH 2026 · PS 26165 · Oil India Limited**

A worker walks up to a box on the wall, presses a button, says what they saw,
and walks away. The report is transcribed, classified into the same four
priority buckets as every other Sentinel report, and appears in the same review
queue — and the worker sees the verdict on the device before they leave.

The point is reach, not novelty. The Stage 0-3 reasoning engine is only as
useful as the reports that reach it, and a written near-miss form is a barrier
for anyone on a rig floor in gloves, in the rain, mid-shift, or more fluent in
spoken Assamese than in written English. Speech removes the filing cost from the
one person who actually saw the hazard.

---

## Status

| Piece | State |
|---|---|
| Device HTTP protocol + state machine | Designed and implemented |
| Firmware: AP, HTTP server, PSRAM capture, clip streaming | Written, **not yet flashed** |
| Microphone driver | Written for I2S and analog — **pins and part not yet confirmed** |
| Display | Text-only UI layer written; SSD1306 backend wired, others stubbed |
| Laptop bridge (poll → STT → pipeline → verdict) | Implemented |
| Backend `POST /api/v1/voice/ingest` | Implemented, tested, **verified end to end** |
| Priority classification of spoken reports | Verified — see below |

The backend half is proven with 8 passing tests. The firmware is complete but
uncompiled, because the microphone and display part numbers are still open. See
[Open hardware questions](#open-hardware-questions).

---

## How it fits together

```
   worker speaks
        │
        ▼
┌──────────────────┐   hosts WiFi AP "SENTINEL-VOICE-01"  (192.168.4.1)
│  ESP32-S3 N16R8  │   captures 16 kHz mono → PSRAM → serves as WAV
│  mic + display   │   shows the verdict when it comes back
└────────┬─────────┘
         │  laptop JOINS the node's network and polls it
         ▼
┌──────────────────┐   faster-whisper, local (the AP has no internet)
│  bridge (laptop) │   transcript + provenance
└────────┬─────────┘
         ▼
┌──────────────────────────────────────────────────────────┐
│  POST /api/v1/voice/ingest                               │
│    run_single()  ── the SAME Stage 0-3 path as a typed   │
│                     report, not a parallel voice model   │
│    → bucket, sif_potential, confidence, lsr_tag          │
└────────┬─────────────────────────────────────────────────┘
         │
         ├─▶ reports table (source="voice") → review queue, dashboard
         └─▶ back to the node's display
```

Full endpoint contract and the reasoning behind the polling direction:
[docs/protocol.md](docs/protocol.md).

---

## The one design decision that matters

**A spoken report is not classified by a separate, softer model.** The transcript
goes through `run_single()` — the identical function `/api/v1/reports/submit`
calls — so it earns its priority on the same evidence and the same reasoning
chain as a typed report.

The alternative, a "voice classifier" tuned for short informal speech, would put
two different definitions of SIF potential in one system. The priority a worker
is shown at the device would then mean something different from the priority a
reviewer sees in the queue, and no one could say which was right. There is a test
that fails if this ever drifts:

```
backend/tests/test_voice_api.py::test_spoken_and_typed_reports_get_the_same_verdict
```

### Verified priority routing

Spoken through the real endpoint, classified by the real engine:

| What was said | Bucket | SIF | Conf. | LSR |
|---|---|---|---|---|
| "…crane was lifting a pipe joint directly over two workers standing under the suspended load, no barricade and no banksman" | `HIGH_CONF_SIF` | yes | 0.977 | Safe Mechanical Lifting |
| "The tea room light on the ground floor is flickering…" | `HIGH_CONF_NON_SIF` | no | 0.634 | — |

---

## Honesty constraints this feature has to respect

The rest of this project is careful about not claiming more than it does, and a
microphone invites two specific overclaims.

**The transcript is a machine's guess at what was said.** Every voice report
carries `voice_provenance` — the ASR model, its confidence, the language, the
audio duration, and the clip filename — through to the console, and is stored
under its own `source="voice"` rather than being folded in with reports a person
typed and checked. A reviewer disputing a wording can pull the original WAV,
which the bridge keeps in `captures/` next to a JSON sidecar.

**ASR confidence is not SIF confidence.** "We may have misheard this" and "this
may not be a precursor" are different doubts. They are deliberately kept as two
separate numbers; collapsing them would make a clean recording of an ambiguous
hazard indistinguishable from a garbled recording of an obvious one.

**The device decides nothing.** It captures audio and displays a verdict computed
on the laptop. It does not transcribe, classify, alarm, or act. Free-form
code-mixed site speech is not something an ESP32-S3 can transcribe, and firmware
that pretended otherwise would be the weakest claim in the project.

**A known weakness, stated rather than hidden:** spoken reports are shorter than
typed ones, and the pipeline currently clears thin reports confidently rather
than routing them to `NEEDS_MORE_INFO`. "Something looked wrong near the pump
today" comes back `HIGH_CONF_NON_SIF` at 0.636. That is existing pipeline
behaviour, not something this feature introduced, but voice makes it easier to
hit — the fix belongs in the routing thresholds, not here.

---

## Running it

### 1. Install the bridge dependencies **while you still have internet**

Once the laptop joins the node's access point it has no route out, and
faster-whisper downloads its model on first use.

```bash
pip install -r esp32/bridge/requirements.txt
```

### 2. Warm the model cache and prove the path with no hardware

`--dry-run` takes any WAV and runs the full transcribe → classify → dashboard
path, so the workflow is demonstrable before the ESP32 is wired.

```bash
python esp32/bridge/sentinel_voice_bridge.py --dry-run --wav some_recording.wav --site duliajan
```

### 3. With the device

```bash
# Flash esp32/firmware/sentinel_voice_node/ from the Arduino IDE
#   Board: ESP32S3 Dev Module · PSRAM: OPI PSRAM · Flash: 16MB

# Backend on the laptop (localhost stays reachable on any network)
uvicorn backend.main:app --port 8000

# Join WiFi "SENTINEL-VOICE-01"  (password in config.h), then:
python esp32/bridge/sentinel_voice_bridge.py --site duliajan
```

Press the button, speak, and the report appears in the console under **All
Reports** filtered by `source=voice`, and in the review queue at its bucket.

> While the laptop is on the node's AP it has no internet. The console is served
> by your own backend on localhost, so it keeps working; anything that needs the
> outside world will not.

---

## Open hardware questions

Everything below is a `TODO(hardware)` in
[firmware/sentinel_voice_node/config.h](firmware/sentinel_voice_node/config.h),
which is the only file that should need editing once the parts are confirmed.

1. **Which microphone?** The firmware supports both, selected by `MIC_MODE`:
   - **Digital I2S MEMS** (INMP441, SPH0645, ICS-43434) — preferred. Needs BCLK,
     WS, DIN pins. Clean, no ADC noise.
   - **Analog module** (MAX9814, MAX4466, KY-038) — needs one ADC1 pin. Noisier.
     If it is a KY-038 or similar, use the **AO** pin; the **DO** pin is a
     comparator trip and cannot reconstruct speech.

2. **Which display?** The UI layer is text-only and driver-agnostic — it renders
   at most three short lines and a level bar, so an SSD1306 OLED, an ST7735/
   ILI9341 TFT or a 16x2 character LCD all work. Only the SSD1306 backend is
   wired up; tell me the panel and I will fill in the matching branch. With
   `DISPLAY_DRIVER = DISPLAY_NONE` the node prints to serial and stays fully
   functional.

3. **Recording trigger.** Defaulted to the **BOOT button on GPIO0**, which every
   ESP32-S3 devkit already has, so the workflow needs no extra hardware to
   demonstrate. Swap in a real push-to-talk button by changing one pin.
   Voice-activated start exists behind `TRIGGER_VOICE_ACTIVATED` but is off by
   default: an always-listening node on a live plant records machinery, and every
   false clip is a report a human has to dismiss.

---

## Layout

```
esp32/
  README.md                    this file
  docs/protocol.md             device HTTP contract + why the laptop polls
  firmware/sentinel_voice_node/
    sentinel_voice_node.ino    AP, HTTP server, state machine
    config.h                   ← the only file to edit for new hardware
    mic.h / mic.cpp            I2S or analog capture into PSRAM
    display.h / display.cpp    driver-agnostic 5-state worker UI
    wav.h                      44-byte PCM WAV header
  bridge/
    sentinel_voice_bridge.py   poll → transcribe → classify → verdict
    requirements.txt
  captures/                    WAV + JSON sidecar per report (gitignored)
```

Backend additions live with the rest of the API, not here:
`POST /api/v1/voice/ingest` in [`backend/main.py`](../backend/main.py),
`VoiceProvenance` / `VoiceReportIngestRequest` in
[`backend/schemas.py`](../backend/schemas.py), tests in
[`backend/tests/test_voice_api.py`](../backend/tests/test_voice_api.py).
