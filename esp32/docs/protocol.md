# Sentinel Voice Node — device protocol

The ESP32-S3 is the **access point and the HTTP server**; the laptop is a client
on its network. That inversion drives the whole design, so it is worth stating
plainly before the endpoint list.

## Why the laptop pulls instead of the device pushing

The device is the DHCP server, so it has a fixed, known address (`192.168.4.1`)
and the laptop does not. If the ESP32 pushed audio to the laptop it would first
have to discover a lease that changes between sessions — mDNS on an isolated AP,
or a registration handshake, both of which fail quietly and are miserable to
debug at a demo table.

Polling a gateway whose address is a constant has none of that failure surface.
A clip is a few hundred kilobytes and the interaction is one worker at a time,
so a 750 ms poll costs nothing and never desynchronises.

**Consequence worth planning for: while the laptop is joined to this AP it has no
internet.** Every step after capture — speech-to-text included — must run
locally. This is why the bridge uses a local Whisper model rather than a hosted
transcription API.

## Endpoints (device, `http://192.168.4.1`)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/status` | Cheap poll target. Current state + clip availability. |
| `GET` | `/api/clip?seq=N` | The buffered recording as a 16 kHz mono WAV. |
| `POST` | `/api/result` | Bridge returns the verdict so the display can show it. |
| `POST` | `/api/ack?seq=N` | Bridge confirms receipt; device frees the buffer. |
| `GET` | `/api/health` | Uptime, free PSRAM, mic status. |

### `GET /api/status`

```json
{
  "device_id": "sentinel-voice-01",
  "state": "ready",
  "seq": 7,
  "clip_ready": true,
  "clip_bytes": 384044,
  "sample_rate": 16000,
  "duration_s": 12.0,
  "free_psram": 7734016
}
```

`seq` increments once per completed recording and is the idempotency key. The
bridge only acts when `clip_ready` is true **and** `seq` is greater than the last
one it processed, so a duplicated poll or a bridge restart cannot double-file a
report.

### `POST /api/result`

The verdict travels back so the worker learns something before walking away —
a report that vanishes into a laptop teaches nobody anything.

```json
{ "seq": 7, "bucket": "HIGH_CONF_SIF", "sif_potential": true,
  "confidence": 0.82, "lsr_tag": "Energy Isolation", "report_id": "obs_a1b2c3" }
```

## Device state machine

```
IDLE ──button──▶ ARMED ──▶ RECORDING ──silence/timeout──▶ READY
                                                            │
                                              bridge GET /api/clip
                                                            ▼
                                                        UPLOADING
                                                            │
                                              bridge POST /api/result
                                                            ▼
 IDLE ◀────── ack + display timeout ────────────────────  RESULT
```

`READY` is durable: the clip sits in PSRAM until the bridge acknowledges it. If
the laptop is closed mid-report, the recording survives and is collected when the
bridge comes back — nothing is lost to a dropped socket.

## What the device deliberately does not do

It does not transcribe, classify, or decide anything. It captures audio and
displays a verdict computed elsewhere. Speech-to-text on free-form, code-mixed
Assamese/Hindi/English site speech is not something an ESP32-S3 can do, and a
device that pretended otherwise would be the weakest claim in the project.
