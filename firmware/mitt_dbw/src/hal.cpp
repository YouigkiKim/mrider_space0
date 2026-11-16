// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0

#include "hal.h"

#include <QuadEncoder.h>
#include <Watchdog_t4.h>
#include <Wire.h>
#include <math.h>

#include "mitt_config.h"

namespace mitt {
namespace hal {
namespace {

constexpr uint8_t kAS5600 = 0x36;
constexpr uint8_t kRegStatus = 0x0B;
constexpr uint8_t kRegRawHi = 0x0C;
constexpr uint8_t kStatusMD = 0x20;  // magnet detected
constexpr uint8_t kStatusML = 0x10;  // too weak
constexpr uint8_t kStatusMH = 0x08;  // too strong

// Channel 1, A = pin 0, B = pin 1, 0 = no internal pull-up (external 10 k on the signal board)
QuadEncoder g_enc(kEncoderChannel, kPinEncA, kPinEncB, 0);

// RTWDOG (WDT3). Its timeout argument is in MILLISECONDS (the library divides by 1/32 ms for
// the 32 kHz LPO clock).
WDT_T4<WDT3> g_wdt;
bool g_last_reset_wdt = false;

uint32_t PulseUsToDuty(float us) {
  const float counts = us * (float)kPwmFrameHz * (float)(1u << kPwmResolutionBits) / 1.0e6f;
  return (uint32_t)lroundf(counts);
}

bool ReadReg(uint8_t reg, uint8_t* buf, uint8_t n) {
  Wire.beginTransmission(kAS5600);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(kAS5600, n) != n) return false;
  for (uint8_t i = 0; i < n; ++i) buf[i] = (uint8_t)Wire.read();
  return true;
}

}  // namespace

void BeginWatchdog() {
  g_last_reset_wdt = (SRC_SRSR & SRC_SRSR_WDOG3_RST_B) != 0;
  SRC_SRSR = SRC_SRSR_WDOG3_RST_B;  // sticky flag, write-1-to-clear

  WDT_timings_t cfg;
  cfg.timeout = kWatchdogMs;  // ms
  cfg.window = 0;             // the library turns this into a 1-tick (~31 us) window
  cfg.callback = nullptr;     // no pre-reset interrupt: a hang must end in a reset, nothing else
  g_wdt.begin(cfg);
}

bool LastResetWasWatchdog() { return g_last_reset_wdt; }

void FeedWatchdog() { g_wdt.feed(); }

void BeginSafeOutputs() {
  pinMode(kPinRelayGate, OUTPUT);
  digitalWriteFast(kPinRelayGate, LOW);  // STOCK

  analogWriteResolution(kPwmResolutionBits);
  analogWriteFrequency(kPinPwmSteer, (float)kPwmFrameHz);  // pins 2 and 3 share FlexPWM4.2
  analogWriteFrequency(kPinPwmDrive, (float)kPwmFrameHz);
  analogWrite(kPinPwmSteer, PulseUsToDuty(kPulseNeutralUs));
  analogWrite(kPinPwmDrive, PulseUsToDuty(kPulseNeutralUs));

  pinMode(kPinLoopToggle, OUTPUT);
}

void BeginInputs() {
  Wire.begin();
  Wire.setClock(100000);  // 100 kHz: bench README / 03-electrical "noise margin over speed"
  g_enc.setInitConfig();
  g_enc.init();
}

AngleSample ReadAngleSensor() {
  AngleSample s;
  uint8_t st = 0;
  uint8_t raw[2] = {0, 0};
  if (!ReadReg(kRegStatus, &st, 1)) return s;
  if (!ReadReg(kRegRawHi, raw, 2)) return s;
  s.i2c_ok = true;
  s.magnet_ok = (st & kStatusMD) && !(st & kStatusML) && !(st & kStatusMH);
  s.raw = (uint16_t)(((raw[0] & 0x0F) << 8) | raw[1]);
  return s;
}

int32_t ReadDriveTicks() { return g_enc.read(); }

void ToggleLoopPin() { digitalToggleFast(kPinLoopToggle); }

}  // namespace hal
}  // namespace mitt
