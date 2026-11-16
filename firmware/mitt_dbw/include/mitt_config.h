// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0
//
// mitt_config.h -- every number the DBW firmware depends on, in ONE place.
//
// THIS BUILD: Stage 0, SENSING ONLY (docs/build/04-firmware.md §4.3). It reads the steering angle
// sensor and the drive encoder and publishes them; it commands nothing. Both pulse lines sit at
// exactly 1500 us and the relay gate LOW. Features are added one stage at a time.
//
// 표기 규칙
//   [FROZEN]   docs/build/04-firmware.md 핀 표 / dbw.md §12 수치 계약에서 온 값. 여기서 바꾸지 말 것.
//   [SPEC]     설계 문서가 정한 값 (dbw.md, safety.md).
//   [MEASURE]  차량에서 측정해 채워야 하는 값. 기본값은 자리표시자(placeholder)일 뿐.
//   [POLICY]   문서가 정하지 않아 정한 값. 팀에서 확정 후 기록할 것.
//
// This header is plain C++ (no Arduino.h) so the host unit tests can include it.

#pragma once

#include <stdint.h>

namespace mitt {

// ---------------------------------------------------------------------------
// Pins [FROZEN] -- docs/build/04-firmware.md "The pin assignment"
// ---------------------------------------------------------------------------
constexpr uint8_t kPinEncA = 0;         // drive Hall latch A (QDC)                    READ
constexpr uint8_t kPinEncB = 1;         // drive Hall latch B (QDC)                    READ
constexpr uint8_t kPinPwmSteer = 2;     // -> signal MUX -> MDDS30 RC1 (steering)     held at 1500 us
constexpr uint8_t kPinPwmDrive = 3;     // -> signal MUX -> MDDS30 RC2 (rear motors)  held at 1500 us
constexpr uint8_t kPinIbusRx = 15;      // Serial3 RX, i-BUS                           not used yet
constexpr uint8_t kPinSda = 18;         // Wire, fixed by hardware (AS5600)            READ
constexpr uint8_t kPinScl = 19;         // Wire, fixed by hardware                     READ
constexpr uint8_t kPinEstopSense = 20;  // E-stop sense                                not used yet
constexpr uint8_t kPinRelayGate = 21;   // relay MUX gate                              held LOW (STOCK)
constexpr uint8_t kPinLoopToggle = 13;  // on-board LED; toggles once per tick -> scope the loop rate

constexpr uint8_t kEncoderChannel = 1;  // QuadEncoder(ch, 0, 1, 0), same as bench/quad_count

// ---------------------------------------------------------------------------
// Rates
// ---------------------------------------------------------------------------
constexpr uint32_t kControlHz = 200;      // [SPEC] loop rate the steering loop will need (ADR E)
constexpr uint32_t kStatusHz = 200;       // [SPEC] Stage 0 gate: /mitt/dbw/status >= 50 Hz
constexpr uint32_t kWatchdogMs = 250;     // [POLICY] RTWDOG (WDT3), fed once per completed loop

// ---------------------------------------------------------------------------
// Pulse lines: held at neutral in this build (the MDDS30 calibrates its centre on the pulse
// present at its power-up, so the lines must never boot at anything else).
// ---------------------------------------------------------------------------
constexpr float kPulseNeutralUs = 1500.0f;  // [SPEC] "exactly 1.5 ms"
constexpr uint32_t kPwmFrameHz = 50;        // [MEASURE] at Stage 1 (dbw.md §12)
constexpr uint8_t kPwmResolutionBits = 15;  // 50 Hz / 15 bit -> 0.61 us per count

// ---------------------------------------------------------------------------
// Steering angle (calibration.md §1: theta = k * (raw - c0), left = +)
// ---------------------------------------------------------------------------
constexpr float kPi = 3.14159265358979f;
constexpr float kDeg = kPi / 180.0f;

constexpr float kSteerLimitRad = 0.3927f;              // [FROZEN] +-22.5 deg road-wheel
constexpr uint16_t kSteerC0Default = 2048;             // [MEASURE] overridden by EEPROM after
                                                       // /mitt/dbw/zero_steering
constexpr float kSteerDegPerCount = 360.0f / 4096.0f;  // [MEASURE] k = (thL-thR)/(cL-cR); may be < 0

// Plausibility (safety.md §2 row 9: "plausibility + range check each loop")
constexpr float kSensorPlausibleMarginRad = 3.0f * kDeg;  // |angle| > limit + this = fault
constexpr float kSensorMaxStepRad = 3.0f * kDeg;          // per tick (600 deg/s): a jump = fault
constexpr uint32_t kSensorClearMs = 200;                  // healthy this long before it clears

// ---------------------------------------------------------------------------
// Drive encoder
// ---------------------------------------------------------------------------
constexpr int32_t kDriveTicksSign = +1;       // [MEASURE] forward rotation must INCREASE ticks
constexpr float kWheelCircumferenceM = 0.80f; // [MEASURE] rollout, calibration.md §2
constexpr int32_t kTicksPerWheelRev = 36;     // [MEASURE] 18 magnets -> 9 cycles x4 (bench quad_count)
constexpr float kMetersPerTick = kWheelCircumferenceM / kTicksPerWheelRev;  // replace with the
                                              // measured meters_per_tick (06-bench-test odometry)
constexpr uint32_t kSpeedWindowMs = 200;      // wheel-speed window; resolution ~0.11 m/s at 36 t/rev

// ---------------------------------------------------------------------------
// micro-ROS
// ---------------------------------------------------------------------------
constexpr const char* kNodeName = "mitt_dbw";
constexpr const char* kTopicStatus = "/mitt/dbw/status";
constexpr const char* kTopicDebug = "/mitt/dbw/debug";            // std_msgs/Float32MultiArray
constexpr const char* kServiceZero = "/mitt/dbw/zero_steering";   // std_srvs/Trigger
constexpr uint32_t kAgentPingPeriodMs = 1000;
constexpr int kAgentPingTimeoutMs = 10;
constexpr uint8_t kAgentPingFailLimit = 3;
constexpr int kEntityTimeoutMs = 30;      // per-entity creation round trip, keeps reconnects short
constexpr int kTimeSyncTimeoutMs = 20;
constexpr uint32_t kTimeSyncPeriodMs = 60000;

}  // namespace mitt
