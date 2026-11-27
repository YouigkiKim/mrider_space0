// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0
//
// Bench: open-loop steering effort, effort SIGN, frame rate, and the watchdog HANG test.
// Stage 1 (docs/build/04-firmware.md §4.4): steering motor only, CURRENT-LIMITED bench supply,
// Teensy pin 2 -> Pololu MUX master -> MDDS30 RC1, motor Left -> steering motor.
// Pin 3 (drive) sits at exactly 1500 us unless a drive key is pressed.
// Stage 2 addition (wheels OFF the ground, §4.5): q/w/e and a/s/d give the drive channel the same
// capped 1 s pulses, so its sign can be seen before anything closes a loop on it.
//
// POWER-UP ORDER (MDDS30 SW6=0 calibrates its centre on whatever pulse it sees at power-up):
//   receiver + Teensy first (this sketch emits 1500 us immediately) -> MUX settled -> driver.
//
// WHAT THIS PROVES
// ----------------
//   1. EFFORT SIGN, before any loop is closed (m2-dbw-steering: "verify the effort sign with a
//      small fixed positive effort"). Press 2: +0.10 effort for 1 s. The sketch reports which
//      way the AS5600 moved. The firmware's angle is  kSteerDegPerCount * (raw - c0),  so with
//      the same kSteerDegPerCount as mitt_config.h, +effort must make that angle GROW.
//      If it shrinks, set kSteerEffortSign = -1 in mitt_config.h (and write down why).
//   2. FRAME RATE: press f to step 50 -> 100 -> 200 -> 300 Hz and see whether the MDDS30 still
//      follows (dbw.md §12: "not pinned, measure at Stage 1"). Scope pin 2 to confirm.
//   3. SIGNAL-LOSS TIMEOUT (SW6=0): hold an effort, press the Teensy's reset button -> the
//      motor must STOP, not latch.
//   4. HANG: press H. +0.10 effort, then `while (true) {}` with the watchdog armed exactly like
//      the firmware (RTWDOG, 250 ms, fed only from the loop). The pulse timer keeps emitting the
//      last width during the hang -- the motor must stop within ~250 ms + 100 ms. If it keeps
//      running, the watchdog is not armed. Record the period beside the result.
//
// Keys:  1/2/3 = steer +0.05/+0.10/+0.15 for 1 s    4/5/6 = steer -0.05/-0.10/-0.15 for 1 s
//        q/w/e = drive +0.05/+0.10/+0.15 for 1 s    a/s/d = drive -0.05/-0.10/-0.15 for 1 s
//        S / D / B = sine on steer / drive / both: amplitude 0.10, period 2 s, 3 cycles, then neutral
//        0 or space = both neutral now (also ends a sine)    f = next frame rate (only while neutral)
//        H = hang test (steering channel)

#include <Arduino.h>
#include <Watchdog_t4.h>
#include <Wire.h>

namespace {

constexpr uint8_t kPinSteer = 2;
constexpr uint8_t kPinDrive = 3;
constexpr uint8_t kResBits = 15;
constexpr float kNeutralUs = 1500.0f;
constexpr float kSpanUs = 500.0f;
constexpr float kEffortCap = 0.15f;     // open loop on a bench: never more than this
constexpr uint32_t kPulseMs = 1000;     // every press is a 1 s pulse, then back to neutral
constexpr uint32_t kWatchdogMs = 250;   // keep equal to mitt_config.h kWatchdogMs
constexpr float kSteerDegPerCount = 360.0f / 4096.0f;  // keep equal to mitt_config.h

constexpr float kFrameRates[] = {50.0f, 100.0f, 200.0f, 300.0f};
int g_rate_idx = 0;

constexpr uint8_t kAS5600 = 0x36;

WDT_T4<WDT3> g_wdt;

// The loop is paced exactly like firmware/mitt_dbw (5 ms tick, ONE feed per tick, no wait for the
// host in setup), because that pattern is the one proven on this watchdog. WDT_T4 clamps window = 0
// up to its minimum and turns WINDOW MODE ON (~31 us, see firmware/mitt_dbw/src/hal.cpp); a refresh
// that comes too soon is invalid and resets the chip. A free-spinning loop that fed every pass, plus
// a `while (!Serial)` wait that fed in a tight loop, was the reset loop seen 2026-11-23/24.
constexpr uint32_t kTickUs = 5000;  // 200 Hz, = mitt_dbw kControlHz
uint32_t g_next_tick_us = 0;
bool g_banner_done = false;

float g_effort = 0.0f;
uint32_t g_effort_until_ms = 0;
float g_drive = 0.0f;  // drive channel, open loop, same cap and 1 s pulse as steering
uint32_t g_drive_until_ms = 0;

// Sine: a smooth open-loop sweep to watch both directions in one go. Under kEffortCap, bounded in
// time, and recomputed every loop pass so the watchdog still sees a live loop.
constexpr float kSineAmp = 0.10f;
constexpr uint32_t kSinePeriodMs = 2000;
constexpr uint32_t kSineCycles = 3;
bool g_sine_steer = false;
bool g_sine_drive = false;
uint32_t g_sine_t0_ms = 0;
uint32_t g_sine_print_ms = 0;
bool g_hang_armed = false;
uint32_t g_hang_at_ms = 0;
int32_t g_raw_at_start = -1;
uint32_t g_last_print_ms = 0;

float Rate() { return kFrameRates[g_rate_idx]; }

uint32_t Duty(float us) {
  return (uint32_t)lroundf(us * Rate() * (float)(1u << kResBits) / 1e6f);
}

void WritePulses() {
  float e = g_effort;
  if (e > kEffortCap) e = kEffortCap;
  if (e < -kEffortCap) e = -kEffortCap;
  analogWrite(kPinSteer, Duty(e == 0.0f ? kNeutralUs : kNeutralUs + e * kSpanUs));
  float d = g_drive;
  if (d > kEffortCap) d = kEffortCap;
  if (d < -kEffortCap) d = -kEffortCap;
  analogWrite(kPinDrive, Duty(d == 0.0f ? kNeutralUs : kNeutralUs + d * kSpanUs));
}

bool SineActive() { return g_sine_steer || g_sine_drive; }

void StopSine() {
  if (!SineActive()) return;
  g_sine_steer = g_sine_drive = false;
  g_effort = 0.0f;
  g_drive = 0.0f;
  WritePulses();
  Serial.println(F("SINE end -> both neutral"));
}

void StartSine(bool steer, bool drive) {
  StopSine();
  g_effort = 0.0f;
  g_drive = 0.0f;
  g_sine_steer = steer;
  g_sine_drive = drive;
  g_sine_t0_ms = millis();
  g_sine_print_ms = 0;
  Serial.printf("SINE %s%s: amplitude %.2f, period %lu ms, %lu cycles. 0/space stops.\n",
                steer ? "steer " : "", drive ? "drive" : "", (double)kSineAmp,
                (unsigned long)kSinePeriodMs, (unsigned long)kSineCycles);
}

void StartDrive(float d) {
  StopSine();
  g_drive = d;
  g_drive_until_ms = millis() + kPulseMs;
  WritePulses();
  Serial.printf("DRIVE %+.2f for %lu ms  (pulse %.1f us) -- which way did the wheels turn?\n", (double)d,
                (unsigned long)kPulseMs, (double)(kNeutralUs + d * kSpanUs));
}

void EndDrive() {
  if (g_drive == 0.0f) return;
  g_drive = 0.0f;
  WritePulses();
  Serial.println(F("  -> drive neutral"));
}

bool ReadRaw(int32_t* out) {
  Wire.beginTransmission(kAS5600);
  Wire.write(0x0C);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(kAS5600, (uint8_t)2) != 2) return false;
  const uint8_t hi = (uint8_t)Wire.read();
  const uint8_t lo = (uint8_t)Wire.read();
  *out = ((int32_t)(hi & 0x0F) << 8) | lo;
  return true;
}

int32_t WrapDiff(int32_t a, int32_t b) {
  int32_t d = a - b;
  if (d > 2047) d -= 4096;
  if (d < -2048) d += 4096;
  return d;
}

void StartEffort(float e) {
  StopSine();
  int32_t raw = -1;
  g_raw_at_start = ReadRaw(&raw) ? raw : -1;
  g_effort = e;
  g_effort_until_ms = millis() + kPulseMs;
  WritePulses();
  Serial.printf("effort %+.2f for %lu ms  (pulse %.1f us)\n", (double)e, (unsigned long)kPulseMs,
                (double)(kNeutralUs + e * kSpanUs));
}

void EndEffort() {
  const float e = g_effort;
  g_effort = 0.0f;
  WritePulses();
  int32_t raw = -1;
  if (e != 0.0f && g_raw_at_start >= 0 && ReadRaw(&raw)) {
    const int32_t d = WrapDiff(raw, g_raw_at_start);
    const float deg = (float)d * kSteerDegPerCount;
    Serial.printf("  -> neutral. raw moved %+ld counts = %+.2f deg (with kSteerDegPerCount %.5f)\n",
                  (long)d, (double)deg, (double)kSteerDegPerCount);
    if (abs(d) < 3) {
      Serial.println(F("     barely moved: effort below the driver/motor deadband, or no power"));
    } else if ((deg > 0) == (e > 0)) {
      Serial.println(F("     +effort -> +angle : kSteerEffortSign = +1"));
    } else {
      Serial.println(F("     +effort -> -angle : kSteerEffortSign = -1"));
    }
  }
}

}  // namespace

void setup() {
  // Watchdog first, then outputs -- the same order as the firmware.
  WDT_timings_t cfg;
  cfg.timeout = kWatchdogMs;  // milliseconds for WDT3
  g_wdt.begin(cfg);

  analogWriteResolution(kResBits);
  analogWriteFrequency(kPinSteer, Rate());
  analogWriteFrequency(kPinDrive, Rate());
  WritePulses();  // exactly 1500 us on both, immediately

  Wire.begin();
  Wire.setClock(100000);

  // NO Serial.begin() and NO wait for the host: on Teensy 4 Serial.begin() blocks up to 2 s for the
  // host to open the port, which starves the watchdog armed above. USB CDC needs no begin(). The
  // banner is printed from the loop once a host opens the port.
  g_next_tick_us = micros() + kTickUs;  // first feed one full tick after the watchdog is armed
}

void PrintBanner() {
  Serial.println();
  Serial.println(F("MRider bench -- steering/drive effort, sign, sine, frame rate, hang test"));
  Serial.println(F("CURRENT-LIMITED SUPPLY, WHEELS OFF. steer 1/2/3 +, 4/5/6 -; drive q/w/e +, a/s/d -;"));
  Serial.println(F("S/D/B = sine steer/drive/both; 0 or space = stop; f = frame rate; H = hang test (250 ms)"));
  Serial.printf("frame rate %.0f Hz\n\n", (double)Rate());
}

void loop() {
  // 5 ms tick, the same pacing as firmware/mitt_dbw ServiceTick(): nothing runs between ticks.
  const uint32_t now_us = micros();
  if ((int32_t)(now_us - g_next_tick_us) < 0) return;
  g_next_tick_us += kTickUs;
  if ((int32_t)(now_us - g_next_tick_us) >= 0) g_next_tick_us = now_us + kTickUs;  // overran: no burst

  const uint32_t now = millis();
  if (!g_banner_done && Serial) {
    g_banner_done = true;
    PrintBanner();
  }

  while (Serial.available() > 0) {
    const int c = Serial.read();
    switch (c) {
      case '1': StartEffort(+0.05f); break;
      case '2': StartEffort(+0.10f); break;
      case '3': StartEffort(+0.15f); break;
      case '4': StartEffort(-0.05f); break;
      case '5': StartEffort(-0.10f); break;
      case '6': StartEffort(-0.15f); break;
      case 'q': StartDrive(+0.05f); break;
      case 'w': StartDrive(+0.10f); break;
      case 'e': StartDrive(+0.15f); break;
      case 'a': StartDrive(-0.05f); break;
      case 's': StartDrive(-0.10f); break;
      case 'd': StartDrive(-0.15f); break;
      case 'S': StartSine(true, false); break;
      case 'D': StartSine(false, true); break;
      case 'B': StartSine(true, true); break;
      case '0':
      case ' ': StopSine(); EndEffort(); EndDrive(); break;
      case 'f':
        if (g_effort != 0.0f || g_drive != 0.0f) {
          Serial.println(F("frame rate changes only at neutral"));
          break;
        }
        g_rate_idx = (g_rate_idx + 1) % (int)(sizeof(kFrameRates) / sizeof(kFrameRates[0]));
        analogWriteFrequency(kPinSteer, Rate());
        analogWriteFrequency(kPinDrive, Rate());
        WritePulses();
        Serial.printf("frame rate %.0f Hz (period %.2f ms) -- does the driver still follow?\n",
                      (double)Rate(), (double)(1000.0f / Rate()));
        break;
      case 'H':
        StartEffort(+0.10f);
        g_effort_until_ms = now + 60000;  // hold it; the hang comes first
        g_hang_armed = true;
        g_hang_at_ms = now + 300;
        Serial.println(F("HANG in 300 ms. Time the motor: it must stop within ~350 ms."));
        Serial.flush();
        break;
      default: break;
    }
  }

  if (SineActive()) {
    const uint32_t el = now - g_sine_t0_ms;
    if (el >= kSinePeriodMs * kSineCycles) {
      StopSine();
    } else {
      const float v = kSineAmp * sinf(6.2831853f * (float)el / (float)kSinePeriodMs);
      if (g_sine_steer) g_effort = v;
      if (g_sine_drive) g_drive = v;
      g_effort_until_ms = now + kPulseMs;  // the 1 s pulse timers must not end a running sine
      g_drive_until_ms = now + kPulseMs;
      WritePulses();
      if ((uint32_t)(now - g_sine_print_ms) >= 100u) {
        g_sine_print_ms = now;
        int32_t raw = -1;
        const bool ok = ReadRaw(&raw);
        Serial.printf("  sine t %5lu ms  steer %+.3f  drive %+.3f  AS5600 %s%ld\n",
                      (unsigned long)el, (double)g_effort, (double)g_drive, ok ? "" : "n/a ",
                      ok ? (long)raw : 0L);
      }
    }
  } else {
    if (g_effort != 0.0f && (int32_t)(now - g_effort_until_ms) >= 0) EndEffort();
    if (g_drive != 0.0f && (int32_t)(now - g_drive_until_ms) >= 0) EndDrive();
  }

  if (g_hang_armed && (int32_t)(now - g_hang_at_ms) >= 0) {
    // Outputs are written, the watchdog is NOT fed: exactly the failure row 8 describes.
    while (true) {
    }
  }

  if (g_effort != 0.0f && !g_hang_armed && !SineActive() && (uint32_t)(now - g_last_print_ms) >= 50u) {
    g_last_print_ms = now;
    int32_t raw = -1;
    if (ReadRaw(&raw) && g_raw_at_start >= 0) {
      Serial.printf("  t %4lu ms  raw %4ld  d %+5ld\n",
                    (unsigned long)(kPulseMs - (g_effort_until_ms - now)), (long)raw,
                    (long)WrapDiff(raw, g_raw_at_start));
    }
  }

  g_wdt.feed();  // once per 5 ms tick, at the end of a complete pass -- never in a tight loop
}
