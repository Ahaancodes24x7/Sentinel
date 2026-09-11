#pragma once
#include <Arduino.h>
#include "config.h"

// ---------------------------------------------------------------------------
// Worker-facing screen.
//
// Deliberately text-only and driver-agnostic: the node has five things to say
// and none of them need graphics. That keeps an unknown "old display" a
// solvable problem — whatever the panel turns out to be, it has to render at
// most three short lines and a 0-100 level bar.
//
// The wording matters as much as the wiring. A worker who has just reported a
// hazard needs to know it was heard and what happens next; "HIGH PRIORITY /
// ROUTED FOR REVIEW" does that, a bucket enum string does not.
// ---------------------------------------------------------------------------

namespace ui {

enum Screen {
  SCREEN_BOOT,       // bringing up mic + AP
  SCREEN_IDLE,       // "PRESS TO REPORT"
  SCREEN_RECORDING,  // live level bar + elapsed seconds
  SCREEN_HOLDING,    // clip captured, waiting for the laptop to collect it
  SCREEN_SENDING,    // bridge is pulling the clip / running the pipeline
  SCREEN_RESULT,     // the verdict came back
  SCREEN_FAULT       // mic dead, PSRAM missing, nothing to pretend about
};

void begin();

void showBoot(const char* line);
void showIdle(bool bridgeSeen);
void showRecording(uint8_t levelPct, uint8_t seconds);
void showHolding();
void showSending();

// `bucket` is the pipeline's routing decision, passed through verbatim from the
// backend. Rendered as plain language, not as the enum.
void showResult(const char* bucket, bool sifPotential, float confidence, const char* lsrTag);

void showFault(const char* reason);

}  // namespace ui
