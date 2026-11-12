// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0

#include "calibration.h"

#include <EEPROM.h>

#include "mitt_config.h"

namespace mitt {
namespace calib {
namespace {

constexpr int kAddr = 0;
constexpr uint32_t kMagic = 0x4D445A30;  // "MDZ0"

struct Record {
  uint32_t magic;
  uint16_t c0;
  uint16_t check;  // ~c0, so a half-written record is rejected
};

uint16_t g_c0 = kSteerC0Default;
bool g_from_eeprom = false;

}  // namespace

void Load() {
  Record r;
  EEPROM.get(kAddr, r);
  if (r.magic == kMagic && r.check == (uint16_t)~r.c0 && r.c0 < 4096) {
    g_c0 = r.c0;
    g_from_eeprom = true;
  } else {
    g_c0 = kSteerC0Default;
    g_from_eeprom = false;
  }
}

bool SaveC0(uint16_t c0) {
  if (c0 >= 4096) return false;
  Record r{kMagic, c0, (uint16_t)~c0};
  EEPROM.put(kAddr, r);
  Record back;
  EEPROM.get(kAddr, back);
  if (back.magic != r.magic || back.c0 != r.c0 || back.check != r.check) return false;
  g_c0 = c0;
  g_from_eeprom = true;
  return true;
}

uint16_t C0() { return g_c0; }
bool C0FromEeprom() { return g_from_eeprom; }

float RawToRad(uint16_t raw) {
  int32_t d = (int32_t)raw - (int32_t)g_c0;
  if (d > 2047) d -= 4096;
  if (d < -2048) d += 4096;
  return kSteerDegPerCount * (float)d * kDeg;
}

}  // namespace calib
}  // namespace mitt
