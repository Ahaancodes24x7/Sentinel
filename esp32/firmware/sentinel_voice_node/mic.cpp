#include "mic.h"

#if MIC_MODE == MIC_MODE_I2S
  #include <ESP_I2S.h>            // Arduino-ESP32 core 3.x
  static I2SClass i2s;
#endif

namespace {

int16_t* g_buf        = nullptr;      // PSRAM, AUDIO_MAX_SECONDS worth
size_t   g_capacity   = 0;            // in samples
size_t   g_count      = 0;            // samples captured so far
size_t   g_clipCount  = 0;            // samples in the completed clip
bool     g_recording  = false;
bool     g_ready      = false;
uint16_t g_rms        = 0;
uint32_t g_lastVoiceMs = 0;
uint32_t g_startedMs   = 0;
const char* g_err     = "";

// Scratch block pulled from the peripheral each poll(). 1024 samples at 16 kHz
// is 64 ms — small enough that loop() stays responsive to the HTTP server,
// large enough that we are not thrashing the I2S driver.
constexpr size_t kBlock = 1024;
int16_t g_block[kBlock];

uint16_t rmsOf(const int16_t* s, size_t n) {
  if (!n) return 0;
  uint64_t acc = 0;
  for (size_t i = 0; i < n; ++i) { int32_t v = s[i]; acc += (uint64_t)(v * v); }
  return (uint16_t)sqrt((double)(acc / n));
}

// Reads one block from whichever peripheral is fitted. Returns samples written.
size_t readBlock() {
#if MIC_MODE == MIC_MODE_I2S
  // The S3 hands back left-aligned 32-bit slots; shift down to int16.
  static int32_t raw[kBlock];
  size_t bytes = i2s.readBytes((char*)raw, sizeof(raw));
  size_t n = bytes / sizeof(int32_t);
  for (size_t i = 0; i < n; ++i) g_block[i] = (int16_t)(raw[i] >> MIC_I2S_GAIN_SHIFT);
  return n;

#else  // MIC_MODE_ANALOG
  // Busy-read at the sample rate. Crude, but an analog module is a fallback
  // path and this keeps it dependency-free. A digital mic avoids all of this.
  const uint32_t periodUs = 1000000UL / AUDIO_SAMPLE_RATE;
  for (size_t i = 0; i < kBlock; ++i) {
    uint32_t t0 = micros();
    // 12-bit ADC centred near mid-rail; remove the DC bias and scale to int16.
    int v = analogRead(MIC_ADC_PIN) - 2048;
    g_block[i] = (int16_t)constrain(v * 16, -32768, 32767);
    while ((micros() - t0) < periodUs) { /* pace to the sample clock */ }
  }
  return kBlock;
#endif
}

}  // namespace

namespace mic {

bool begin() {
  if (!psramFound()) {
    g_err = "PSRAM not found - enable OPI PSRAM in board settings";
    return false;
  }
  g_capacity = (size_t)AUDIO_SAMPLE_RATE * AUDIO_MAX_SECONDS;
  g_buf = (int16_t*)ps_malloc(g_capacity * sizeof(int16_t));
  if (!g_buf) { g_err = "PSRAM allocation failed"; return false; }

#if MIC_MODE == MIC_MODE_I2S
  i2s.setPins(MIC_I2S_BCLK, MIC_I2S_WS, -1, MIC_I2S_DIN);
  if (!i2s.begin(I2S_MODE_STD, AUDIO_SAMPLE_RATE,
                 I2S_DATA_BIT_WIDTH_32BIT,
                 MIC_I2S_LEFT_CHANNEL ? I2S_SLOT_MODE_MONO : I2S_SLOT_MODE_MONO)) {
    g_err = "I2S begin failed - check BCLK/WS/DIN wiring";
    return false;
  }
#else
  analogReadResolution(12);
  analogSetPinAttenuation(MIC_ADC_PIN, ADC_11db);
#endif

  g_ready = true;
  return true;
}

bool ready() { return g_ready; }
const char* lastError() { return g_err; }

void startRecording() {
  g_count = 0;
  g_clipCount = 0;
  g_recording = true;
  g_startedMs = millis();
  g_lastVoiceMs = g_startedMs;
}

bool poll() {
  if (!g_recording) return false;

  size_t n = readBlock();
  if (n) {
    size_t room = g_capacity - g_count;
    size_t take = n < room ? n : room;
    memcpy(g_buf + g_count, g_block, take * sizeof(int16_t));
    g_count += take;
    g_rms = rmsOf(g_block, n);
    if (g_rms >= AUDIO_SILENCE_RMS) g_lastVoiceMs = millis();
  }

  const uint32_t elapsed = millis() - g_startedMs;
  const bool full    = g_count >= g_capacity;
  const bool longEnough = elapsed >= (uint32_t)AUDIO_MIN_SECONDS * 1000;
  const bool wentQuiet  = (millis() - g_lastVoiceMs) >= AUDIO_SILENCE_STOP_MS;

  if (full || (longEnough && wentQuiet)) { stopRecording(); return false; }
  return true;
}

void stopRecording() {
  if (!g_recording) return;
  g_recording = false;
  g_clipCount = g_count;
}

bool isRecording()          { return g_recording; }
uint16_t currentRms()       { return g_rms; }
const int16_t* clipSamples(){ return g_buf; }
size_t clipSampleCount()    { return g_clipCount; }
float  clipSeconds()        { return (float)g_clipCount / (float)AUDIO_SAMPLE_RATE; }

}  // namespace mic
