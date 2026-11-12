// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0
//
// micro-ROS node "mitt_dbw" over USB serial (micro_ros_agent on the laptop). Stage 0: sensing only.
//
//   pub  /mitt/dbw/status         mitt_msgs/DbwStatus         best-effort  (200 Hz)
//   pub  /mitt/dbw/debug          std_msgs/Float32MultiArray  best-effort  (200 Hz)
//   srv  /mitt/dbw/zero_steering  std_srvs/Trigger            (store c0 in EEPROM)
//
// DbwStatus in this build: steering_angle, wheel_speed, drive_ticks are live; mode is always
// ESTOP (0); faults is 0 or FAULT_ENCODER (1); steering_setpoint is 0.
//
// /mitt/dbw/debug data[] layout -- keep in sync with PublishStatus():
//   0 AS5600 raw (0..4095)   1 I2C answered (0/1)   2 magnet in range (0/1)   3 c0
//   4 last reset was the watchdog (0/1)
//
// WHY BEST-EFFORT: a RELIABLE micro-ROS publisher waits for the agent's acknowledgement inside
// rcl_publish (up to 1000 ms), which would stall the loop past the 250 ms watchdog. `ros2 topic
// echo/hz` adapt automatically; a laptop node must subscribe with a best-effort profile.
//
// Agent loss is handled by ping + reconnect. Every blocking step during (re)connection calls
// `between()` so the loop keeps running and keeps feeding the watchdog.

#pragma once

#include <stddef.h>
#include <stdint.h>

namespace mitt {
namespace uros {

struct Sample {
  float steering_angle = 0.0f;  // rad, last trustworthy value
  float wheel_speed = 0.0f;     // m/s
  int32_t drive_ticks = 0;      // sign-corrected
  uint16_t faults = 0;
  uint16_t raw = 0;
  bool i2c_ok = false;
  bool magnet_ok = false;
  uint16_t c0 = 0;
  bool wdt_reset = false;
};

using ZeroHandler = bool (*)(char* msg, size_t cap);  // /mitt/dbw/zero_steering

void Begin(ZeroHandler zero);
void Spin(void (*between)());
bool Connected();
void Publish(const Sample& s, uint32_t sample_us);

}  // namespace uros
}  // namespace mitt
