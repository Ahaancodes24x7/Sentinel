#pragma once
// ---------------------------------------------------------------------------
// Sentinel Voice Node — build configuration
//
// This is the ONLY file you should need to edit when the exact microphone and
// display parts are known. Everything marked TODO(hardware) is a placeholder
// with a working default, not a guess that is silently relied on elsewhere.
//
// Target: ESP32-S3 N16R8  (16 MB flash, 8 MB PSRAM)
// Arduino IDE / arduino-cli board settings that matter:
//   Board:      "ESP32S3 Dev Module"
//   PSRAM:      "OPI PSRAM"        <-- required; audio buffers live in PSRAM
//   Flash Size: "16MB (128Mb)"
//   Partition:  "16M Flash (3MB APP/9.9MB FATFS)"
// ---------------------------------------------------------------------------

// --- Identity ---------------------------------------------------------------
#define DEVICE_ID        "sentinel-voice-01"
#define FIRMWARE_VERSION "0.1.0"

// The site this node is physically installed at. Must match a site_id the
// backend knows (see GET /api/v1/sites): duliajan | naharkatiya | moran ...
#define DEVICE_SITE      "duliajan"

// --- Access point -----------------------------------------------------------
// The device hosts the network; the laptop joins it. Device is always 192.168.4.1.
#define AP_SSID     "SENTINEL-VOICE-01"
#define AP_PASSWORD "sentinel2026"      // >= 8 chars, or the AP silently opens
#define AP_CHANNEL  6
#define AP_MAX_CONN 4

// --- Audio ------------------------------------------------------------------
// 16 kHz mono 16-bit is what Whisper wants natively. Anything else costs a
// resample on the laptop for no gain in intelligibility of site speech.
#define AUDIO_SAMPLE_RATE 16000
#define AUDIO_BITS        16
#define AUDIO_CHANNELS    1

// Recording ceiling. 30 s at the settings above is ~960 KB, which PSRAM holds
// comfortably and which fits Whisper's 30 s window without chunking.
#define AUDIO_MAX_SECONDS 30
#define AUDIO_MIN_SECONDS 2      // shorter than this is treated as a misfire

// Stop early once the worker stops talking, so nobody has to hold a button for
// the full 30 s to file a five-second observation.
#define AUDIO_SILENCE_STOP_MS 2500
#define AUDIO_SILENCE_RMS     380     // TODO(hardware): calibrate to your mic

// --- Microphone -------------------------------------------------------------
// TODO(hardware): set MIC_MODE and the pins once the part is confirmed.
//
//   MIC_MODE_I2S    — digital MEMS: INMP441, SPH0645, ICS-43434, MSM261.
//                     Preferred. Clean, no ADC noise, no biasing.
//   MIC_MODE_ANALOG — analog module: MAX9814, MAX4466, KY-038, LM393 boards.
//                     Uses ADC1 + a timer. Noisier; keep leads short.
//
// If you have a KY-038 / LM393 board, note it has BOTH an analog pin (AO) and a
// digital threshold pin (DO). Use AO. The DO pin is a comparator trip, not audio,
// and cannot reconstruct speech.
#define MIC_MODE_I2S    1
#define MIC_MODE_ANALOG 2
#define MIC_MODE        MIC_MODE_I2S     // TODO(hardware)

// I2S pins (used when MIC_MODE == MIC_MODE_I2S)
#define MIC_I2S_BCLK  4      // TODO(hardware) SCK / BCLK
#define MIC_I2S_WS    5      // TODO(hardware) WS / LRCL
#define MIC_I2S_DIN   6      // TODO(hardware) SD / DOUT of the mic
#define MIC_I2S_PORT  I2S_NUM_0

// INMP441/SPH0645 sit on the LEFT channel when L/R is tied to GND. If your
// recordings come back as silence, this is the first thing to flip.
#define MIC_I2S_LEFT_CHANNEL true

// Analog pin (used when MIC_MODE == MIC_MODE_ANALOG). Must be an ADC1 GPIO —
// ADC2 is unusable while WiFi is active, which it always is here.
#define MIC_ADC_PIN 7        // TODO(hardware)

// Digital MEMS mics deliver 18-24 significant bits left-aligned in a 32-bit
// slot; this shift brings them down to int16. 11-14 is the usual useful range.
#define MIC_I2S_GAIN_SHIFT 11

// --- Trigger ----------------------------------------------------------------
// Default is the BOOT button, present on every ESP32-S3 devkit — the workflow
// needs no extra hardware to be demonstrable. Wire a proper weatherproof
// push-to-talk button later and only this pin changes.
#define TRIGGER_BUTTON_PIN     0     // GPIO0 = BOOT, active LOW
#define TRIGGER_BUTTON_ACTIVE  LOW
#define TRIGGER_DEBOUNCE_MS    45

// Voice-activated start, for when a gloved worker cannot press anything.
// Off by default: on a live plant an always-listening node records machinery,
// and every false clip is a report a human has to dismiss.
#define TRIGGER_VOICE_ACTIVATED 0

// --- Display ----------------------------------------------------------------
// TODO(hardware): pick the driver once the panel is identified. The UI layer
// (display.h) is text-only and driver-agnostic on purpose, so an SSD1306 OLED,
// an ST7735/ILI9341 TFT or even a 16x2 character LCD can back it unchanged.
#define DISPLAY_NONE     0
#define DISPLAY_SSD1306  1   // 128x64 I2C OLED
#define DISPLAY_ST7735   2   // 128x160 SPI TFT
#define DISPLAY_ILI9341  3   // 240x320 SPI TFT
#define DISPLAY_LCD1602  4   // 16x2 character LCD over I2C
#define DISPLAY_DRIVER   DISPLAY_SSD1306   // TODO(hardware)

#define DISPLAY_I2C_SDA  8   // TODO(hardware)
#define DISPLAY_I2C_SCL  9   // TODO(hardware)
#define DISPLAY_I2C_ADDR 0x3C

// SPI pins, only used by the TFT drivers
#define DISPLAY_SPI_CS   10  // TODO(hardware)
#define DISPLAY_SPI_DC   11  // TODO(hardware)
#define DISPLAY_SPI_RST  12  // TODO(hardware)

// How long the verdict stays on screen before returning to IDLE.
#define DISPLAY_RESULT_MS 9000

// --- Behaviour --------------------------------------------------------------
// The clip is held until the bridge acknowledges it, so a closed laptop does not
// lose a report. After this long unacknowledged we drop it rather than blocking
// the node forever on a bridge that is never coming back.
#define CLIP_RETENTION_MS 180000
