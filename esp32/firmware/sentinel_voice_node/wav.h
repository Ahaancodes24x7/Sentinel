#pragma once
#include <Arduino.h>
#include "config.h"

// Minimal 44-byte canonical WAV header. Written ahead of the PCM so the laptop
// receives a file ffmpeg/Whisper opens directly, with no client-side framing.
namespace wav {

inline void writeHeader(uint8_t* h, uint32_t pcmBytes) {
  const uint32_t sr       = AUDIO_SAMPLE_RATE;
  const uint16_t ch       = AUDIO_CHANNELS;
  const uint16_t bits     = AUDIO_BITS;
  const uint32_t byteRate = sr * ch * bits / 8;
  const uint16_t align    = ch * bits / 8;
  const uint32_t riffSize = 36 + pcmBytes;

  memcpy(h + 0,  "RIFF", 4);   memcpy(h + 4,  &riffSize, 4);
  memcpy(h + 8,  "WAVE", 4);   memcpy(h + 12, "fmt ", 4);
  const uint32_t fmtLen = 16;  memcpy(h + 16, &fmtLen, 4);
  const uint16_t pcmFmt = 1;   memcpy(h + 20, &pcmFmt, 2);
  memcpy(h + 22, &ch, 2);      memcpy(h + 24, &sr, 4);
  memcpy(h + 28, &byteRate, 4);memcpy(h + 32, &align, 2);
  memcpy(h + 34, &bits, 2);    memcpy(h + 36, "data", 4);
  memcpy(h + 40, &pcmBytes, 4);
}

constexpr size_t kHeaderBytes = 44;  // canonical PCM WAV header

}  // namespace wav
