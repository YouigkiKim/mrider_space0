// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0
//
// Hardware abstraction for the Teensy 4.1 DBW board. Everything that touches a pin lives here;
// nothing here decides anything.
//
// Stage 0 build: inputs only. Both pulse lines are held at exactly 1500 us and the relay gate
// LOW (STOCK); nothing in this build changes them.

#pragma once

#include <Arduino.h>

namespace mitt {
namespace hal {

// ---- Boot order (safety.md §3, 04-firmware §4.3):
//   1. watchdog armed  -- "enabled at boot, before any output is driven"
//   2. relay gate LOW (STOCK), both pulse lines at exactly 1500 us
void BeginWatchdog();
bool LastResetWasWatchdog();
void FeedWatchdog();       // ONLY from the loop, after a complete read of every sensor
void BeginSafeOutputs();
void BeginInputs();        // AS5600 I2C, quadrature decoder

// ---- Steering angle sensor (AS5600, I2C 0x36, 100 kHz)
struct AngleSample {
  bool i2c_ok = false;
  bool magnet_ok = false;  // STATUS: MD set, ML/MH clear
  uint16_t raw = 0;        // 0..4095
};
AngleSample ReadAngleSensor();

// ---- Drive encoder (QDC on pins 0/1). Raw count; kDriveTicksSign is applied by the caller.
int32_t ReadDriveTicks();

// ---- Scope point for the loop rate (pin 13 / LED)
void ToggleLoopPin();

}  // namespace hal
}  // namespace mitt
