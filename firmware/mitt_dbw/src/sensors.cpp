// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0

#include "sensors.h"

#include <math.h>

namespace mitt {

void AngleCheck::Update(bool read_ok, float angle_rad, uint32_t now_us) {
  bool good = read_ok && isfinite(angle_rad) &&
              fabsf(angle_rad) <= kSteerLimitRad + kSensorPlausibleMarginRad;
  if (good && have_prev_ && fabsf(angle_rad - prev_) > kSensorMaxStepRad) good = false;

  if (!good) {
    ok_ = false;
    have_prev_ = false;  // continuity is broken; the next sample is not judged against this one
    good_run_ = false;
    return;
  }
  prev_ = angle_rad;
  have_prev_ = true;
  if (!good_run_) {
    good_run_ = true;
    good_since_us_ = now_us;
  }
  // Unsigned difference: correct across the ~71 min micros() rollover.
  if (!ok_ && (uint32_t)(now_us - good_since_us_) >= kSensorClearMs * 1000u) ok_ = true;
}

void WheelSpeed::Update(int32_t ticks, uint32_t now_us) {
  ticks_[head_] = ticks;
  us_[head_] = now_us;
  head_ = (head_ + 1) % kRing;
  if (count_ < kRing) ++count_;
  const int oldest = (count_ < kRing) ? 0 : head_;
  const uint32_t span_us = now_us - us_[oldest];
  mps_ = (span_us > 0) ? (float)(ticks - ticks_[oldest]) * kMetersPerTick / (span_us * 1e-6f)
                       : 0.0f;
}

}  // namespace mitt
