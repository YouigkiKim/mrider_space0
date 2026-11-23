// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0
//
// Bench: BNO085 IMU on the Teensy's SECOND I2C bus -- docs/build/04-firmware.md "Bring up the IMU",
// docs/design/sensors.md §3 (decided 2026-11-16).
//
// WIRING
// ------
//   IMU SDA -> pin 17 (SDA1)    IMU SCL -> pin 16 (SCL1)    IMU power -> Teensy 3.3 V    GND -> GND
//   NOT on pins 18/19: Wire carries the AS5600 and nothing else.
//   Pull-ups: Wire1 needs them and the signal board has none. Meter SDA1/SCL1 to the IMU's supply pin
//   with everything unpowered: a few kOhm = the breakout has them; open = add 4.7 k to 3.3 V.
//
// WHAT THIS PROVES, in order
// --------------------------
//   1. Wire  (18/19): exactly one device, 0x36 -- the IMU did not land on the steering sensor's bus.
//   2. Wire1 (17/16): exactly one device, 0x4A or 0x4B -- the 04-firmware.md pass condition.
//   3. Product ID over SHTP: the thing at that address is a BNO08x and speaks SH-2 (prints its
//      firmware version). An address that ACKs but never answers here is a wiring or mode problem.
//   4. The fused orientation (rotation vector, 100 Hz) as yaw / pitch / roll, and the nine raw axes
//      it is fused from -- accelerometer and gyroscope at 50 Hz, magnetometer at 25 Hz -- every
//      250 ms, with each report's rate. Turn and tilt the board by hand: the angles must follow;
//      at rest the accelerometer reads ~9.8 m/s^2 on the axis pointing up and the gyro reads ~0.
//      The I2C budget at 100 kHz is why only the rotation vector runs at 100 Hz here.
//
// Wire1 runs at 100 kHz: the breakouts seen so far carry 10 k on SCL, which is marginal at 400 kHz.
// Self-contained on purpose (same rule as the other bench sketches): no library, no shared code.

#include <Arduino.h>
#include <Wire.h>

namespace {

constexpr uint32_t kBusHz = 100000;
constexpr uint8_t kAS5600 = 0x36;
constexpr uint8_t kChunk = 32;             // bytes per I2C read, the 4-byte header included
constexpr uint32_t kRotUs = 10000;         // rotation vector, 100 Hz
constexpr uint32_t kAccGyrUs = 20000;      // accelerometer, gyroscope, 50 Hz
constexpr uint32_t kMagUs = 40000;         // magnetometer, 25 Hz

uint8_t g_addr = 0;
uint8_t g_seq[6] = {0};
uint8_t g_pkt[320];
uint16_t g_len = 0;
uint8_t g_chan = 0;

uint32_t g_n_rot = 0, g_n_acc = 0, g_n_gyr = 0, g_n_mag = 0;   // reports since the last print
uint32_t g_last_report_ms = 0;
uint32_t g_last_print_ms = 0;
float g_yaw = 0, g_pitch = 0, g_roll = 0;
float g_a[3] = {0}, g_g[3] = {0}, g_m[3] = {0};
uint8_t g_acc_rot = 0, g_acc_mag = 0;

int Scan(TwoWire& bus, const char* name, uint8_t* found, int max_found) {
  int n = 0;
  for (uint8_t a = 1; a < 127; ++a) {
    bus.beginTransmission(a);
    if (bus.endTransmission() == 0) {
      if (n < max_found) found[n] = a;
      ++n;
    }
  }
  Serial.printf("%-22s", name);
  if (n == 0) Serial.print(" nothing answered");
  for (int i = 0; i < n && i < max_found; ++i) Serial.printf(" 0x%02X", found[i]);
  Serial.println();
  return n;
}

// One SHTP packet from the BNO08x. Every I2C read starts with a fresh 4-byte header, so a long
// packet is read in chunks, each one dropping its header. Returns the payload length (0 = none).
uint16_t ReadPacket() {
  if (Wire1.requestFrom(g_addr, (uint8_t)4) != 4) return 0;
  uint8_t h[4];
  for (int i = 0; i < 4; ++i) h[i] = Wire1.read();
  const uint16_t total = (uint16_t)(((uint16_t)h[1] << 8) | h[0]) & 0x7FFF;
  if (total <= 4) return 0;
  g_chan = h[2];
  uint16_t remaining = total - 4;
  uint16_t got = 0;
  while (remaining > 0) {
    const uint8_t want = (remaining + 4 > kChunk) ? kChunk : (uint8_t)(remaining + 4);
    const uint8_t n = Wire1.requestFrom(g_addr, want);
    if (n <= 4) break;
    for (int i = 0; i < 4; ++i) Wire1.read();
    for (int i = 4; i < n; ++i) {
      const uint8_t b = Wire1.read();
      if (got < sizeof(g_pkt)) g_pkt[got] = b;
      ++got;
    }
    remaining = (remaining > (uint16_t)(n - 4)) ? (uint16_t)(remaining - (n - 4)) : 0;
  }
  g_len = got < sizeof(g_pkt) ? got : sizeof(g_pkt);
  return g_len;
}

bool SendPacket(uint8_t chan, const uint8_t* data, uint8_t len) {
  Wire1.beginTransmission(g_addr);
  Wire1.write((uint8_t)(len + 4));
  Wire1.write((uint8_t)0);
  Wire1.write(chan);
  Wire1.write(g_seq[chan]++);
  Wire1.write(data, len);
  return Wire1.endTransmission() == 0;
}

void Drain(uint32_t ms) {
  const uint32_t t0 = millis();
  while (millis() - t0 < ms) {
    if (ReadPacket() == 0) delay(5);
  }
}

bool ProductId() {
  const uint8_t req[2] = {0xF9, 0x00};
  if (!SendPacket(2, req, sizeof(req))) return false;
  const uint32_t t0 = millis();
  while (millis() - t0 < 1000) {
    if (ReadPacket() && g_chan == 2 && g_pkt[0] == 0xF8 && g_len >= 16) {
      const uint32_t part = g_pkt[4] | (g_pkt[5] << 8) | ((uint32_t)g_pkt[6] << 16) | ((uint32_t)g_pkt[7] << 24);
      const uint32_t build = g_pkt[8] | (g_pkt[9] << 8) | ((uint32_t)g_pkt[10] << 16) | ((uint32_t)g_pkt[11] << 24);
      Serial.printf("PASS  product ID: SW %u.%u.%u  part %lu  build %lu  (reset cause %u)\n", g_pkt[2],
                    g_pkt[3], (unsigned)(g_pkt[12] | (g_pkt[13] << 8)), (unsigned long)part,
                    (unsigned long)build, g_pkt[1]);
      return true;
    }
    delay(5);
  }
  return false;
}

bool EnableReport(uint8_t id, uint32_t interval_us) {
  uint8_t f[17] = {0};
  f[0] = 0xFD;  // Set Feature command
  f[1] = id;
  for (int i = 0; i < 4; ++i) f[5 + i] = (uint8_t)(interval_us >> (8 * i));
  const bool ok = SendPacket(2, f, sizeof(f));
  delay(10);
  return ok;
}

int16_t S16(const uint8_t* p) { return (int16_t)(p[0] | (p[1] << 8)); }

// x, y, z of a 10-byte calibrated sensor report, scaled by its Q point
void Xyz(const uint8_t* r, int q, float* out) {
  const float k = 1.0f / (float)(1 << q);
  for (int i = 0; i < 3; ++i) out[i] = S16(&r[4 + 2 * i]) * k;
}

void ParseReports() {
  uint16_t i = 0;
  while (i < g_len) {
    const uint8_t id = g_pkt[i];
    if (id == 0xFB || id == 0xFA) {  // timestamp base / rebase
      i += 5;
      continue;
    }
    if ((id == 0x01 || id == 0x02 || id == 0x03) && i + 10 <= g_len) {
      if (id == 0x01) {  // accelerometer, m/s^2, Q8
        Xyz(&g_pkt[i], 8, g_a);
        ++g_n_acc;
      } else if (id == 0x02) {  // gyroscope (calibrated), rad/s, Q9
        Xyz(&g_pkt[i], 9, g_g);
        ++g_n_gyr;
      } else {  // magnetic field (calibrated), uT, Q4
        Xyz(&g_pkt[i], 4, g_m);
        g_acc_mag = g_pkt[i + 2] & 0x03;
        ++g_n_mag;
      }
      g_last_report_ms = millis();
      i += 10;
      continue;
    }
    if (id == 0x05 && i + 14 <= g_len) {
      const float q = 1.0f / 16384.0f;  // Q14
      const float x = S16(&g_pkt[i + 4]) * q, y = S16(&g_pkt[i + 6]) * q;
      const float z = S16(&g_pkt[i + 8]) * q, w = S16(&g_pkt[i + 10]) * q;
      g_acc_rot = g_pkt[i + 2] & 0x03;
      g_roll = atan2f(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)) * 57.29578f;
      float s = 2 * (w * y - z * x);
      s = s > 1 ? 1 : (s < -1 ? -1 : s);
      g_pitch = asinf(s) * 57.29578f;
      g_yaw = atan2f(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)) * 57.29578f;
      ++g_n_rot;
      g_last_report_ms = millis();
      i += 14;
      continue;
    }
    break;  // anything else: stop reading this packet
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);
  const uint32_t t0 = millis();
  while (!Serial && (millis() - t0) < 4000) {
  }
  Serial.println();
  Serial.println(F("MRider bench -- IMU check (BNO085 on Wire1: SDA1 = 17, SCL1 = 16)"));

  uint8_t found[8];
  Wire.begin();
  Wire.setClock(kBusHz);
  const int n0 = Scan(Wire, "Wire  (18/19):", found, 8);
  if (n0 == 1 && found[0] == kAS5600) {
    Serial.println(F("PASS  0x36 alone on Wire."));
  } else {
    Serial.println(F("WARN  Wire should carry 0x36 and nothing else (AS5600 unplugged, or the IMU is here?)"));
  }

  Wire1.begin();
  Wire1.setClock(kBusHz);
  const int n1 = Scan(Wire1, "Wire1 (17/16):", found, 8);
  if (n1 == 1 && (found[0] == 0x4A || found[0] == 0x4B)) {
    g_addr = found[0];
    Serial.printf("PASS  one IMU at 0x%02X on Wire1.\n", g_addr);
  } else if (n1 == 0) {
    Serial.println(F("FAIL  nothing on Wire1: check SDA1 = 17, SCL1 = 16, IMU power 3.3 V, GND, pull-ups."));
    return;
  } else {
    Serial.println(F("FAIL  expected exactly one device, 0x4A or 0x4B."));
    return;
  }

  Drain(1000);  // the advertisement and reset packets the BNO08x sends after power-up
  if (!ProductId()) {
    Serial.println(F("FAIL  the address answers but no product ID came back (mode pins PS0/PS1? reset?)."));
  }
  const bool ok = EnableReport(0x05, kRotUs) & EnableReport(0x01, kAccGyrUs) &
                  EnableReport(0x02, kAccGyrUs) & EnableReport(0x03, kMagUs);
  Serial.println(ok ? F("reports requested: rotation vector 100 Hz, accel/gyro 50 Hz, mag 25 Hz -- move the board.")
                    : F("FAIL  a Set Feature write was not acknowledged."));
  g_last_print_ms = millis();
}

void loop() {
  if (g_addr == 0) {
    delay(1000);
    return;
  }
  while (ReadPacket()) {
    if (g_chan == 3) ParseReports();
  }
  const uint32_t now = millis();
  if (now - g_last_print_ms >= 250) {
    const float k = 1000.0f / (float)(now - g_last_print_ms);
    if (g_last_report_ms == 0 || now - g_last_report_ms > 1000) {
      Serial.println(F("NO REPORTS -- the IMU stopped answering, or the feature request was not accepted"));
    } else {
      Serial.printf("ANG  yaw %+7.1f  pitch %+6.1f  roll %+7.1f deg          | rot %5.1f/s  accuracy %u/3\n",
                    g_yaw, g_pitch, g_roll, g_n_rot * k, g_acc_rot);
      Serial.printf("RAW  a %+6.2f %+6.2f %+6.2f m/s2 | g %+6.3f %+6.3f %+6.3f rad/s | m %+6.1f %+6.1f %+6.1f uT"
                    " | a %4.1f g %4.1f m %4.1f /s  mag acc %u/3\n",
                    g_a[0], g_a[1], g_a[2], g_g[0], g_g[1], g_g[2], g_m[0], g_m[1], g_m[2], g_n_acc * k,
                    g_n_gyr * k, g_n_mag * k, g_acc_mag);
    }
    g_n_rot = g_n_acc = g_n_gyr = g_n_mag = 0;
    g_last_print_ms = now;
  }
}
