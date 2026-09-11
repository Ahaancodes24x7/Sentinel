#include "display.h"

// The concrete driver is chosen in config.h. Only the SSD1306 path is wired up
// here because that is the most common salvage panel; the others are left as
// explicit, honest stubs rather than code that claims to drive hardware nobody
// has identified yet. Fill in the branch that matches the real panel.
#if DISPLAY_DRIVER == DISPLAY_SSD1306
  #include <Wire.h>
  #include <Adafruit_GFX.h>
  #include <Adafruit_SSD1306.h>
  static Adafruit_SSD1306 oled(128, 64, &Wire, -1);
  #define HAVE_DISPLAY 1
#else
  #define HAVE_DISPLAY 0
#endif

namespace {

// Everything the node says goes through here, so a new driver only has to
// implement "put these lines on the screen".
void render(const char* l1, const char* l2, const char* l3, int barPct) {
#if HAVE_DISPLAY
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);

  oled.setTextSize(1);
  oled.setCursor(0, 0);
  oled.println(l1 ? l1 : "");

  oled.setTextSize(2);
  oled.setCursor(0, 14);
  oled.println(l2 ? l2 : "");

  oled.setTextSize(1);
  oled.setCursor(0, 40);
  oled.println(l3 ? l3 : "");

  if (barPct >= 0) {
    int w = (int)(124.0f * (barPct / 100.0f));
    oled.drawRect(0, 54, 128, 8, SSD1306_WHITE);
    oled.fillRect(2, 56, w, 4, SSD1306_WHITE);
  }
  oled.display();
#else
  // No panel configured yet: the serial console is the display, so the workflow
  // is still fully demonstrable while the real one is being identified.
  Serial.printf("[ui] %s | %s | %s", l1 ? l1 : "", l2 ? l2 : "", l3 ? l3 : "");
  if (barPct >= 0) Serial.printf(" | %d%%", barPct);
  Serial.println();
#endif
}

}  // namespace

namespace ui {

void begin() {
#if HAVE_DISPLAY
  Wire.begin(DISPLAY_I2C_SDA, DISPLAY_I2C_SCL);
  if (!oled.begin(SSD1306_SWITCHCAPVCC, DISPLAY_I2C_ADDR)) {
    Serial.println("[ui] SSD1306 not responding - falling back to serial");
  }
#endif
}

void showBoot(const char* line)      { render("SENTINEL VOICE NODE", "START", line, -1); }
void showIdle(bool bridgeSeen)       { render(bridgeSeen ? "LINKED" : "NO LAPTOP",
                                              "PRESS TO", "REPORT A HAZARD", -1); }
void showRecording(uint8_t pct, uint8_t s) {
  char l3[24]; snprintf(l3, sizeof(l3), "SPEAK NOW  %us", (unsigned)s);
  render("RECORDING", "LISTENING", l3, pct);
}
void showHolding() { render("CAPTURED", "HOLDING", "waiting for laptop", -1); }
void showSending() { render("CAPTURED", "SENDING", "analysing report", -1); }

void showResult(const char* bucket, bool sif, float confidence, const char* lsr) {
  // Plain language, and never a verdict the pipeline did not actually give.
  // NEEDS_MORE_INFO is a real outcome here, not a failure: it means the report
  // was understood but was too thin to route, and the worker can say more.
  const char* headline = "RECORDED";
  const char* detail   = "";
  if      (!strcmp(bucket, "HIGH_CONF_SIF"))     { headline = "HIGH PRIORITY"; detail = "routed for review"; }
  else if (!strcmp(bucket, "LOW_CONF_REVIEW"))   { headline = "FOR REVIEW";    detail = "an HSE reviewer will check"; }
  else if (!strcmp(bucket, "NEEDS_MORE_INFO"))   { headline = "NEED MORE";     detail = "please add detail"; }
  else if (!strcmp(bucket, "HIGH_CONF_NON_SIF")) { headline = "LOGGED";        detail = "no precursor indicated"; }

  char l1[32]; snprintf(l1, sizeof(l1), "%s %d%%", sif ? "PRECURSOR" : "REPORT",
                        (int)(confidence * 100));
  char l3[40]; snprintf(l3, sizeof(l3), "%s%s%s", detail,
                        (lsr && *lsr && strcmp(lsr, "N/A")) ? " | " : "",
                        (lsr && *lsr && strcmp(lsr, "N/A")) ? lsr : "");
  render(l1, headline, l3, -1);
}

void showFault(const char* reason) { render("FAULT", "OFFLINE", reason, -1); }

}  // namespace ui
