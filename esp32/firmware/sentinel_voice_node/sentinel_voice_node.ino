// ---------------------------------------------------------------------------
// Sentinel Voice Node — ESP32-S3 N16R8
//
// A worker walks up, presses the button, says what they saw, and walks away.
// The node captures 16 kHz mono audio into PSRAM and serves it over its own
// WiFi access point. A bridge process on the laptop collects the clip,
// transcribes it locally, and files it through the ordinary Sentinel Stage 0-3
// pipeline — the same code path a typed report takes, so a spoken report is
// triaged into the same four priority buckets and lands in the same review
// queue. The verdict comes back here and goes on the display.
//
// What this device does NOT do: transcribe, classify, or decide anything. See
// docs/protocol.md for why that split is deliberate rather than a limitation
// worked around.
// ---------------------------------------------------------------------------
#include <WiFi.h>
#include <WebServer.h>
#include "config.h"
#include "mic.h"
#include "display.h"
#include "wav.h"

WebServer server(80);

enum NodeState { ST_BOOT, ST_IDLE, ST_RECORDING, ST_READY, ST_UPLOADING, ST_RESULT, ST_FAULT };
static NodeState  g_state       = ST_BOOT;
static uint32_t   g_seq         = 0;       // increments per completed clip
static uint32_t   g_clipAtMs    = 0;       // when the clip became available
static uint32_t   g_resultAtMs  = 0;
static uint32_t   g_lastPollMs  = 0;       // last time the bridge said hello

// Verdict from the laptop, shown on the display.
static char  g_bucket[32] = "";
static char  g_lsr[48]    = "";
static bool  g_sif        = false;
static float g_conf       = 0.0f;

static const char* stateName() {
  switch (g_state) {
    case ST_BOOT:      return "boot";
    case ST_IDLE:      return "idle";
    case ST_RECORDING: return "recording";
    case ST_READY:     return "ready";
    case ST_UPLOADING: return "uploading";
    case ST_RESULT:    return "result";
    default:           return "fault";
  }
}

static bool bridgeSeen() { return g_lastPollMs && (millis() - g_lastPollMs) < 5000; }

// --- HTTP -------------------------------------------------------------------

static void handleStatus() {
  g_lastPollMs = millis();
  const bool clipReady = (g_state == ST_READY || g_state == ST_UPLOADING);
  char body[320];
  snprintf(body, sizeof(body),
    "{\"device_id\":\"%s\",\"fw\":\"%s\",\"site\":\"%s\",\"state\":\"%s\",\"seq\":%u,"
    "\"clip_ready\":%s,\"clip_bytes\":%u,\"sample_rate\":%d,\"duration_s\":%.2f,"
    "\"free_psram\":%u}",
    DEVICE_ID, FIRMWARE_VERSION, DEVICE_SITE, stateName(), (unsigned)g_seq,
    clipReady ? "true" : "false",
    (unsigned)(clipReady ? wav::kHeaderBytes + mic::clipSampleCount() * 2 : 0),
    AUDIO_SAMPLE_RATE, clipReady ? mic::clipSeconds() : 0.0f,
    (unsigned)ESP.getFreePsram());
  server.send(200, "application/json", body);
}

// Streams the clip as a WAV. Chunked so a 30 s recording never needs a second
// contiguous buffer the size of the first.
static void handleClip() {
  if (g_state != ST_READY && g_state != ST_UPLOADING) {
    server.send(409, "application/json", "{\"error\":\"no clip available\"}");
    return;
  }
  const uint32_t pcmBytes = mic::clipSampleCount() * 2;

  g_state = ST_UPLOADING;
  ui::showSending();

  uint8_t header[wav::kHeaderBytes];
  wav::writeHeader(header, pcmBytes);

  server.setContentLength(wav::kHeaderBytes + pcmBytes);
  server.send(200, "audio/wav", "");
  server.sendContent((const char*)header, wav::kHeaderBytes);

  const uint8_t* pcm = (const uint8_t*)mic::clipSamples();
  const size_t   kChunk = 4096;
  for (uint32_t off = 0; off < pcmBytes; off += kChunk) {
    size_t n = (pcmBytes - off) < kChunk ? (pcmBytes - off) : kChunk;
    server.sendContent((const char*)(pcm + off), n);
  }
  server.sendContent("", 0);
}

// The laptop hands the pipeline's verdict back so the worker sees an outcome.
static void handleResult() {
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"error\":\"body required\"}");
    return;
  }
  String body = server.arg("plain");

  // A hand-rolled extractor rather than a JSON library: four scalar fields from
  // a message we define ourselves does not justify the dependency or the heap.
  auto pick = [&](const char* key, String& out) -> bool {
    int k = body.indexOf(String("\"") + key + "\"");
    if (k < 0) return false;
    int c = body.indexOf(':', k);
    if (c < 0) return false;
    int s = c + 1;
    while (s < (int)body.length() && (body[s] == ' ' || body[s] == '"')) s++;
    int e = s;
    while (e < (int)body.length() && body[e] != ',' && body[e] != '"' && body[e] != '}') e++;
    out = body.substring(s, e);
    return true;
  };

  String v;
  if (pick("bucket", v))        strncpy(g_bucket, v.c_str(), sizeof(g_bucket) - 1);
  if (pick("lsr_tag", v))       strncpy(g_lsr, v.c_str(), sizeof(g_lsr) - 1);
  if (pick("sif_potential", v)) g_sif  = v.startsWith("t");
  if (pick("confidence", v))    g_conf = v.toFloat();

  g_state      = ST_RESULT;
  g_resultAtMs = millis();
  ui::showResult(g_bucket, g_sif, g_conf, g_lsr);
  server.send(200, "application/json", "{\"ok\":true}");
}

static void handleAck() {
  // The bridge has the clip safely. Release the buffer for the next worker.
  // A verdict may still arrive separately via /api/result.
  if (g_state == ST_READY) g_state = ST_IDLE;
  server.send(200, "application/json", "{\"ok\":true}");
}

static void handleHealth() {
  char body[220];
  snprintf(body, sizeof(body),
    "{\"ok\":%s,\"uptime_ms\":%u,\"free_heap\":%u,\"free_psram\":%u,\"mic\":\"%s\"}",
    mic::ready() ? "true" : "false", (unsigned)millis(),
    (unsigned)ESP.getFreeHeap(), (unsigned)ESP.getFreePsram(),
    mic::ready() ? "ok" : mic::lastError());
  server.send(200, "application/json", body);
}

// --- Trigger ----------------------------------------------------------------

static bool buttonPressed() {
  static uint32_t lastChange = 0;
  static int      lastRaw    = !TRIGGER_BUTTON_ACTIVE;
  int raw = digitalRead(TRIGGER_BUTTON_PIN);
  if (raw != lastRaw) { lastRaw = raw; lastChange = millis(); return false; }
  if ((millis() - lastChange) < TRIGGER_DEBOUNCE_MS) return false;
  return raw == TRIGGER_BUTTON_ACTIVE;
}

// --- Lifecycle --------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  delay(200);
  ui::begin();
  ui::showBoot("starting");

  pinMode(TRIGGER_BUTTON_PIN, TRIGGER_BUTTON_ACTIVE == LOW ? INPUT_PULLUP : INPUT_PULLDOWN);

  if (!mic::begin()) {
    g_state = ST_FAULT;
    ui::showFault(mic::lastError());
    Serial.printf("[mic] FAULT: %s\n", mic::lastError());
  }

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASSWORD, AP_CHANNEL, false, AP_MAX_CONN);
  Serial.printf("[ap] %s  ip=%s\n", AP_SSID, WiFi.softAPIP().toString().c_str());

  server.on("/api/status", HTTP_GET,  handleStatus);
  server.on("/api/clip",   HTTP_GET,  handleClip);
  server.on("/api/result", HTTP_POST, handleResult);
  server.on("/api/ack",    HTTP_POST, handleAck);
  server.on("/api/health", HTTP_GET,  handleHealth);
  server.begin();

  if (g_state != ST_FAULT) { g_state = ST_IDLE; ui::showIdle(false); }
}

void loop() {
  server.handleClient();
  if (g_state == ST_FAULT) return;

  switch (g_state) {
    case ST_IDLE: {
      static uint32_t lastPaint = 0;
      if (buttonPressed()) {
        mic::startRecording();
        g_state = ST_RECORDING;
        ui::showRecording(0, 0);
      } else if (millis() - lastPaint > 1000) {
        lastPaint = millis();
        ui::showIdle(bridgeSeen());
      }
      break;
    }

    case ST_RECORDING: {
      bool still = mic::poll();
      static uint32_t lastPaint = 0;
      if (millis() - lastPaint > 120) {
        lastPaint = millis();
        uint8_t pct = (uint8_t)constrain(mic::currentRms() / 40, 0, 100);
        ui::showRecording(pct, (uint8_t)mic::clipSeconds());
      }
      if (!still) {
        // A clip shorter than the floor is a misfire, not a report. Discarding
        // it here keeps the reviewer's queue free of accidental button presses.
        if (mic::clipSeconds() < AUDIO_MIN_SECONDS) {
          g_state = ST_IDLE;
          ui::showIdle(bridgeSeen());
        } else {
          g_seq++;
          g_clipAtMs = millis();
          g_state = ST_READY;
          ui::showHolding();
        }
      }
      break;
    }

    case ST_READY:
    case ST_UPLOADING:
      // Hold the clip for the bridge. If the laptop never comes back we give up
      // rather than leaving the node permanently unable to take a new report.
      if (millis() - g_clipAtMs > CLIP_RETENTION_MS) {
        g_state = ST_IDLE;
        ui::showIdle(bridgeSeen());
      }
      break;

    case ST_RESULT:
      if (millis() - g_resultAtMs > DISPLAY_RESULT_MS) {
        g_state = ST_IDLE;
        ui::showIdle(bridgeSeen());
      }
      break;

    default: break;
  }
}
