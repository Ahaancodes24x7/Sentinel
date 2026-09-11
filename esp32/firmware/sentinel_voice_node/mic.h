#pragma once
#include <Arduino.h>
#include "config.h"

// ---------------------------------------------------------------------------
// Microphone capture into a PSRAM ring of int16 PCM.
//
// The rest of the firmware talks to the mic only through this interface, so
// swapping a digital MEMS part for an analog module is a change to config.h and
// this file alone — the state machine, HTTP layer and display never learn which
// kind of microphone is fitted.
// ---------------------------------------------------------------------------

namespace mic {

// Allocates the PSRAM capture buffer and brings up I2S or the ADC.
// Returns false if PSRAM is missing or the peripheral refuses to start; the
// caller surfaces that on the display rather than pretending to record.
bool begin();

bool ready();
const char* lastError();

// Starts a new capture. Discards any clip that was not collected.
void startRecording();

// Pumps samples from the peripheral into the buffer. Call every loop().
// Returns true while still recording, false once it has stopped (on silence,
// on the length ceiling, or because stopRecording() was called).
bool poll();

void stopRecording();
bool isRecording();

// Root-mean-square of the most recent window, for the level meter and for the
// silence detector. Units are raw int16, so it is comparable to
// AUDIO_SILENCE_RMS in config.h.
uint16_t currentRms();

// The completed clip. Valid from the moment poll() returns false until the
// next startRecording().
const int16_t* clipSamples();
size_t         clipSampleCount();
float          clipSeconds();

}  // namespace mic
