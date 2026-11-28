// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0
//
// Bench: E-stop sense (pin 20) and relay gate (pin 21) -- Stage 0 input check and the
// Stage 3 relay MUX test (docs/design/safety.md §6), WHEELS OFF.
//
// WHAT THIS PROVES
// ----------------
//   1. Sense reads HIGH with the button released and the coil supply live, LOW when pressed --
//      and LOW with the sense wire unplugged (INPUT_PULLDOWN: a broken wire must read "stopped").
//   2. No bounce: a single press is a single transition. Bounces within 20 ms are counted.
//   3. Gate HIGH clicks the relays to DBW only while the E-stop is released; pressing the
//      E-stop drops them (the coils are fed through the button's NC contacts -- hardware, not
//      this sketch). The sketch also drops the gate itself the moment sense goes low.
//   4. After a power-up the relays are at STOCK (gate starts LOW, plus the 10 k pulldown).
//
// Both pulse lines sit at EXACTLY 1500 us the whole time, so the MDDS30 (SW6=0) calibrates its
// centre on neutral and nothing moves even with the relays at DBW.
//
// Keys (serial monitor):  g = gate HIGH (DBW, refused while sense is low)   x = gate LOW (STOCK)

#include <Arduino.h>

namespace {

constexpr uint8_t kPinSense = 20;
constexpr uint8_t kPinGate = 21;
constexpr uint8_t kPinPwmSteer = 2;
constexpr uint8_t kPinPwmDrive = 3;
constexpr float kFrameHz = 50.0f;
constexpr uint8_t kResBits = 15;
constexpr uint32_t kBounceMs = 20;

bool g_level = false;
bool g_gate = false;
uint32_t g_last_change_ms = 0;
uint32_t g_transitions = 0;
uint32_t g_bounces = 0;
uint32_t g_last_print_ms = 0;

uint32_t Duty(float us) { return (uint32_t)lroundf(us * kFrameHz * (float)(1u << kResBits) / 1e6f); }

void SetGate(bool on) {
  g_gate = on;
  digitalWriteFast(kPinGate, on ? HIGH : LOW);
  Serial.printf("[%8lu ms] gate %s\n", (unsigned long)millis(), on ? "HIGH -> DBW" : "LOW -> STOCK");
}

}  // namespace

void setup() {
  pinMode(kPinGate, OUTPUT);
  digitalWriteFast(kPinGate, LOW);  // first thing: STOCK

  analogWriteResolution(kResBits);
  analogWriteFrequency(kPinPwmSteer, kFrameHz);
  analogWriteFrequency(kPinPwmDrive, kFrameHz);
  analogWrite(kPinPwmSteer, Duty(1500.0f));
  analogWrite(kPinPwmDrive, Duty(1500.0f));

  pinMode(kPinSense, INPUT_PULLDOWN);

  Serial.begin(115200);
  const uint32_t t0 = millis();
  while (!Serial && (millis() - t0) < 4000) {
  }
  g_level = digitalReadFast(kPinSense);
  g_last_change_ms = millis();

  Serial.println();
  Serial.println(F("MRider bench -- E-stop sense (pin 20) + relay gate (pin 21)"));
  Serial.println(F("Pulse lines held at exactly 1500 us. Keys: g = gate HIGH, x = gate LOW"));
  Serial.printf("sense at boot: %s\n\n", g_level ? "HIGH (energised)" : "LOW (stopped)");
}

void loop() {
  const bool level = digitalReadFast(kPinSense);
  const uint32_t now = millis();
  if (level != g_level) {
    const uint32_t held = now - g_last_change_ms;
    ++g_transitions;
    if (held < kBounceMs) ++g_bounces;
    Serial.printf("[%8lu ms] sense %s  (previous state lasted %lu ms)%s\n", (unsigned long)now,
                  level ? "LOW -> HIGH" : "HIGH -> LOW", (unsigned long)held,
                  held < kBounceMs ? "  ** BOUNCE **" : "");
    g_level = level;
    g_last_change_ms = now;
    if (!level && g_gate) SetGate(false);  // same rule as the firmware: low drops the latch
  }

  while (Serial.available() > 0) {
    const int c = Serial.read();
    if (c == 'g') {
      if (!g_level) {
        Serial.println(F("refused: sense is LOW (E-stop pressed or wire open)"));
      } else {
        SetGate(true);
      }
    } else if (c == 'x') {
      SetGate(false);
    }
  }

  if ((uint32_t)(now - g_last_print_ms) >= 2000u) {
    g_last_print_ms = now;
    Serial.printf("sense %s  gate %s  transitions %lu  bounces %lu\n", g_level ? "HIGH" : "LOW ",
                  g_gate ? "HIGH" : "LOW ", (unsigned long)g_transitions,
                  (unsigned long)g_bounces);
  }
}
