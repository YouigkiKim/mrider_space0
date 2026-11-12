// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0
//
// Steering zero (c0) persistence, calibration.md §1:
//   "Store c0 via the Teensy's ROS 2 zeroing service ... the Teensy persists it (EEPROM) so
//    centre survives reboot."
// The scale k (deg/count) is a compile-time value from config/calibration/steering.yaml,
// copied into mitt_config.h -- it changes only when the sensor is re-mounted.

#pragma once

#include <stdint.h>

namespace mitt {
namespace calib {

void Load();                 // EEPROM -> c0 (falls back to kSteerC0Default if blank/corrupt)
bool SaveC0(uint16_t c0);    // c0 -> EEPROM. Slow (flash emulation): call only in ESTOP.
uint16_t C0();
bool C0FromEeprom();         // false = still using the compiled default

// theta = k * (raw - c0), with the difference wrapped into [-2048, 2047] so a c0 near the
// 0/4095 seam does not produce a 360 deg jump.
float RawToRad(uint16_t raw);

}  // namespace calib
}  // namespace mitt
