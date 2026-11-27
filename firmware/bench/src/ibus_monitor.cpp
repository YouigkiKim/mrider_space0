// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0
//
// Bench: i-BUS monitor -- Stage 2 Layer A prerequisite (docs/build/04-firmware.md §4.5).
//
// BEFORE THE WIRE TOUCHES PIN 15: METER THE i-BUS IDLE LEVEL
// ----------------------------------------------------------
// The FS-iA6B runs on UBEC B (5 V) and the Teensy 4.1 is NOT 5 V tolerant. Idle at ~3.3 V ->
// wire link at R5/R6. Idle at ~5 V -> fit the divider at R5/R6 (03-electrical.md §3.5.4).
// One meter, one minute; the alternative is a dead pin on a socketed-but-soldered board.
//
// WHAT THIS PROVES
// ----------------
//   1. frames arrive on Serial3 RX (pin 15) at 115200 8N1, NOT inverted (~130 frames/s)
//   2. checksums pass -- a stream of bad checksums is a level or ground problem, not code
//   3. the channel map is what the firmware expects (mitt_config.h):
//        CH1 steering  (right stick H)      CH2 throttle (right stick V, self-centring, Mode 2)
//        CH5 MUX SEL   (2-pos switch)       CH6 KILL / MANUAL / AUTO (3-pos SwC)  [POLICY]
//   4. RC LOSS: switch the transmitter OFF and watch the last column.
//        "NO FRAMES"            -> the frame-timeout path will catch RC loss.
//        frames keep coming     -> the receiver is sending FAILSAFE (or held) values. Then the
//                                  transmitter's failsafe for CH6 MUST be set to KILL, or RC loss
//                                  is invisible to the Teensy. Set it, and repeat this test.
//
// Self-contained on purpose (same rule as the other bench sketches): it shares no code with
// firmware/mitt_dbw, so a bug there cannot hide a wiring fault here.

#include <Arduino.h>

namespace {

constexpr uint32_t kBaud = 115200;
constexpr uint32_t kTimeoutMs = 100;  // same RC-loss timeout as mitt_config.h kRcTimeoutMs
constexpr uint16_t kKillBelow = 1250;
constexpr uint16_t kAutoAbove = 1750;

uint8_t g_rx_mem[512];
uint8_t g_buf[32];
uint8_t g_idx = 0;
uint16_t g_ch[14] = {0};
uint32_t g_good = 0;
uint32_t g_bad = 0;
uint32_t g_good_window = 0;
uint32_t g_last_frame_ms = 0;
uint32_t g_last_print_ms = 0;
bool g_ever = false;

bool Feed(uint8_t b) {
  if (g_idx == 0) {
    if (b == 0x20) g_buf[g_idx++] = b;
    return false;
  }
  if (g_idx == 1) {
    if (b == 0x40) {
      g_buf[g_idx++] = b;
    } else {
      g_idx = (b == 0x20) ? 1 : 0;
    }
    return false;
  }
  g_buf[g_idx++] = b;
  if (g_idx < 32) return false;
  g_idx = 0;
  uint16_t sum = 0xFFFF;
  for (int i = 0; i < 30; ++i) sum = (uint16_t)(sum - g_buf[i]);
  if (sum != (uint16_t)(g_buf[30] | (g_buf[31] << 8))) {
    ++g_bad;
    return false;
  }
  for (int c = 0; c < 14; ++c) {
    g_ch[c] = (uint16_t)((g_buf[2 + 2 * c] | (g_buf[3 + 2 * c] << 8)) & 0x0FFF);
  }
  return true;
}

float Norm(uint16_t us) {
  float x = ((float)us - 1500.0f) / 500.0f;
  if (x > 1.0f) x = 1.0f;
  if (x < -1.0f) x = -1.0f;
  return x;
}

const char* ModeName(uint16_t us) {
  if (us < 900 || us > 2100) return "INVALID";
  if (us < kKillBelow) return "KILL";
  if (us > kAutoAbove) return "AUTO";
  return "MANUAL";
}

}  // namespace

void setup() {
  Serial.begin(115200);
  const uint32_t t0 = millis();
  while (!Serial && (millis() - t0) < 4000) {
  }
  Serial3.begin(kBaud);  // RX = pin 15
  Serial3.addMemoryForRead(g_rx_mem, sizeof(g_rx_mem));

  Serial.println();
  Serial.println(F("MRider bench -- i-BUS monitor (Serial3 RX = pin 15, 115200 8N1)"));
  Serial.println(F("METER THE i-BUS IDLE LEVEL FIRST. 5 V on pin 15 kills it."));
  Serial.println(F("Then: move each stick/switch, and finally turn the TX OFF."));
  Serial.println();
}

void loop() {
  while (Serial3.available() > 0) {
    if (Feed((uint8_t)Serial3.read())) {
      ++g_good;
      ++g_good_window;
      g_last_frame_ms = millis();
      g_ever = true;
    }
  }

  const uint32_t now = millis();
  if ((uint32_t)(now - g_last_print_ms) < 250u) return;
  const uint32_t win_ms = now - g_last_print_ms;
  g_last_print_ms = now;
  const float fps = g_good_window * 1000.0f / (float)win_ms;
  g_good_window = 0;

  Serial.printf("CH1 %4u CH2 %4u CH3 %4u CH4 %4u CH5 %4u CH6 %4u | %5.1f fr/s bad %lu | ",
                g_ch[0], g_ch[1], g_ch[2], g_ch[3], g_ch[4], g_ch[5], (double)fps,
                (unsigned long)g_bad);
  Serial.printf("steer %+5.2f thr %+5.2f CH6=%-7s CH5 %s | ", (double)Norm(g_ch[0]),
                (double)Norm(g_ch[1]), ModeName(g_ch[5]), g_ch[4] > 1500 ? "HIGH" : "LOW ");

  const uint32_t age = now - g_last_frame_ms;
  if (!g_ever) {
    Serial.println(F("NO FRAMES YET -- check bind, iBUS servo port, level, ground"));
  } else if (age > kTimeoutMs) {
    Serial.printf("NO FRAMES for %lu ms  -> RC LOSS detectable by timeout\n", (unsigned long)age);
  } else {
    Serial.printf("age %3lu ms OK\n", (unsigned long)age);
  }
}
