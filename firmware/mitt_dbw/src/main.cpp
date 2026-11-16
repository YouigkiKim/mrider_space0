// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0
//
// mitt_dbw -- Teensy 4.1 drive-by-wire controller.
// STAGE 0 BUILD: sensing only (docs/build/04-firmware.md §4.3). Nothing is commanded; both pulse
// lines sit at exactly 1500 us and the relay gate LOW. Features are added one stage at a time.
//
//   AS5600 (I2C 18/19) --------> steering angle  (theta = k * (raw - c0), plausibility-checked)
//   Hall latches (QDC 0/1) ----> drive ticks -> wheel speed
//                                     |
//   laptop <--micro-ROS/USB-- /mitt/dbw/status + /mitt/dbw/debug (200 Hz)
//   laptop --micro-ROS/USB--> /mitt/dbw/zero_steering (store c0)
//
// ONE thread, polled. The 200 Hz tick runs from loop() on a micros() schedule -- deliberately NOT
// from an IntervalTimer interrupt: the watchdog is fed only after a loop iteration that actually
// completed (safety.md §2 row 8), so a hang anywhere (micro-ROS, I2C, ...) stops the feeding.

#include <Arduino.h>
#include <stdio.h>

#include "calibration.h"
#include "hal.h"
#include "mitt_config.h"
#include "sensors.h"
#include "uros_node.h"

using namespace mitt;

namespace {

constexpr uint32_t kTickUs = 1000000u / kControlHz;
constexpr uint32_t kStatusUs = 1000000u / kStatusHz;

AngleCheck g_angle;
WheelSpeed g_wheel;
hal::AngleSample g_sample;
int32_t g_ticks = 0;
uint32_t g_next_tick_us = 0;
uint32_t g_last_tick_us = 0;
uint32_t g_next_status_us = 0;

void Tick(uint32_t now) {
  g_sample = hal::ReadAngleSensor();
  g_angle.Update(g_sample.i2c_ok && g_sample.magnet_ok, calib::RawToRad(g_sample.raw), now);
  g_ticks = hal::ReadDriveTicks() * kDriveTicksSign;
  g_wheel.Update(g_ticks, now);
  hal::ToggleLoopPin();
  g_last_tick_us = now;
  hal::FeedWatchdog();  // only after a complete read of every sensor
}

// Runs the tick if it is due. Called from loop() AND between every blocking micro-ROS step,
// so a reconnect does not starve the loop or the watchdog.
void ServiceTick() {
  const uint32_t now = micros();
  if ((int32_t)(now - g_next_tick_us) < 0) return;
  g_next_tick_us += kTickUs;
  if ((int32_t)(now - g_next_tick_us) >= 0) g_next_tick_us = now + kTickUs;  // overran: no burst
  Tick(now);
}

bool HandleZeroRequest(char* msg, size_t cap) {
  const hal::AngleSample s = hal::ReadAngleSensor();
  if (!s.i2c_ok || !s.magnet_ok) {
    snprintf(msg, cap, "refused: AS5600 not healthy (i2c=%d magnet=%d)", s.i2c_ok, s.magnet_ok);
    return false;
  }
  const uint16_t old_c0 = calib::C0();
  // EEPROM emulation may erase a flash sector here (tens of ms) -- well inside the watchdog,
  // and nothing is driven in this build.
  if (!calib::SaveC0(s.raw)) {
    snprintf(msg, cap, "failed: EEPROM write did not verify");
    return false;
  }
  snprintf(msg, cap, "c0 %u -> %u saved. Copy it to config/calibration/steering.yaml", old_c0,
           s.raw);
  return true;
}

}  // namespace

void setup() {
  hal::BeginWatchdog();     // armed before any output is driven (safety.md §2 row 8)
  hal::BeginSafeOutputs();  // relay LOW, both pulse lines exactly 1500 us
  hal::BeginInputs();
  calib::Load();
  uros::Begin(&HandleZeroRequest);
  g_next_tick_us = micros();
  g_next_status_us = g_next_tick_us;
}

void loop() {
  ServiceTick();
  uros::Spin(&ServiceTick);

  const uint32_t now = micros();
  if ((int32_t)(now - g_next_status_us) >= 0) {
    g_next_status_us = now + kStatusUs;
    uros::Sample s;
    // Show the live reading whenever the sensor answered (even out of range, so calibration can
    // see it move); `faults` says whether it is trustworthy.
    const bool read_ok = g_sample.i2c_ok && g_sample.magnet_ok;
    s.steering_angle = read_ok ? calib::RawToRad(g_sample.raw) : g_angle.last_good_rad();
    s.wheel_speed = g_wheel.mps();
    s.drive_ticks = g_ticks;
    s.faults = g_angle.ok() ? 0 : kFaultEncoder;
    s.raw = g_sample.raw;
    s.i2c_ok = g_sample.i2c_ok;
    s.magnet_ok = g_sample.magnet_ok;
    s.c0 = calib::C0();
    s.wdt_reset = hal::LastResetWasWatchdog();
    uros::Publish(s, g_last_tick_us);
  }
}
