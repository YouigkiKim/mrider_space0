// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0
//
// Sensor interpretation with no Arduino dependency (host-tested in test/host/):
//   AngleCheck  -- is this steering angle trustworthy? (safety.md §2 row 9)
//   WheelSpeed  -- drive encoder counts -> m/s over a short window

#pragma once

#include <stdint.h>

#include "mitt_config.h"

namespace mitt {

// DbwStatus.FAULT_ENCODER: "angle sensor NAK / out of range / magnet lost".
constexpr uint16_t kFaultEncoder = 1;

// Judges every sample: I2C answered, magnet in range, angle physically possible, no jump.
// After any bad sample the sensor must stay good for kSensorClearMs before it is trusted again.
class AngleCheck {
 public:
  void Update(bool read_ok, float angle_rad, uint32_t now_us);
  bool ok() const { return ok_; }
  float last_good_rad() const { return prev_; }

 private:
  bool ok_ = false;
  bool have_prev_ = false;
  float prev_ = 0.0f;
  bool good_run_ = false;
  uint32_t good_since_us_ = 0;
};

class WheelSpeed {
 public:
  void Update(int32_t ticks, uint32_t now_us);  // once per tick, ticks already sign-corrected
  float mps() const { return mps_; }

 private:
  static constexpr int kRing = (int)(kSpeedWindowMs * kControlHz / 1000u) + 1;
  int32_t ticks_[kRing] = {0};
  uint32_t us_[kRing] = {0};
  int head_ = 0;
  int count_ = 0;
  float mps_ = 0.0f;
};

}  // namespace mitt
