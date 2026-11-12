// Host unit tests for sensor interpretation (AngleCheck, WheelSpeed). No Teensy needed.
//
//   ./test/host/run_host_tests.sh

#include <math.h>
#include <stdio.h>

#include "sensors.h"

using namespace mitt;

static int g_fail = 0;
static int g_pass = 0;
#define CHECK(cond)                                             \
  do {                                                          \
    if (cond) {                                                 \
      ++g_pass;                                                 \
    } else {                                                    \
      ++g_fail;                                                 \
      printf("  FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond); \
    }                                                           \
  } while (0)

constexpr uint32_t kTick = 1000000u / kControlHz;
constexpr float kDt = 1.0f / (float)kControlHz;
static void Test(const char* name) { printf("- %s\n", name); }
static bool Near(float a, float b, float tol) { return fabsf(a - b) <= tol; }

// Feed `ms` of samples at a fixed angle.
static void Hold(AngleCheck* c, bool read_ok, float angle, uint32_t ms, uint32_t* t) {
  for (uint32_t i = 0; i < ms * kControlHz / 1000u; ++i) {
    *t += kTick;
    c->Update(read_ok, angle, *t);
  }
}

static float SpinWheel(WheelSpeed* w, float rev_per_s, float seconds, uint32_t* t_us) {
  double ticks = 0.0;
  for (int i = 0; i < (int)(seconds * kControlHz); ++i) {
    *t_us += kTick;
    ticks += rev_per_s * kTicksPerWheelRev * kDt;
    w->Update((int32_t)floor(ticks), *t_us);
  }
  return w->mps();
}

int main() {
  {
    Test("angle: not trusted at boot; trusted after 200 ms of good samples");
    AngleCheck c;
    uint32_t t = 1000;
    CHECK(!c.ok());
    Hold(&c, true, 0.1f, 150, &t);
    CHECK(!c.ok());
    Hold(&c, true, 0.1f, 100, &t);
    CHECK(c.ok());
    CHECK(Near(c.last_good_rad(), 0.1f, 1e-6f));
  }
  {
    Test("angle: I2C failure or lost magnet -> fault at once, keeps the last good value");
    AngleCheck c;
    uint32_t t = 1000;
    Hold(&c, true, 0.2f, 300, &t);
    CHECK(c.ok());
    t += kTick;
    c.Update(false, 0.0f, t);
    CHECK(!c.ok());
    CHECK(Near(c.last_good_rad(), 0.2f, 1e-6f));
  }
  {
    Test("angle: one bad sample costs 200 ms of trust (no flicker back)");
    AngleCheck c;
    uint32_t t = 1000;
    Hold(&c, true, 0.0f, 300, &t);
    t += kTick;
    c.Update(false, 0.0f, t);
    Hold(&c, true, 0.0f, 150, &t);
    CHECK(!c.ok());
    Hold(&c, true, 0.0f, 100, &t);
    CHECK(c.ok());
  }
  {
    Test("angle: beyond the limit + 3 deg is not physically possible -> fault");
    AngleCheck c;
    uint32_t t = 1000;
    Hold(&c, true, kSteerLimitRad + 2.0f * kDeg, 300, &t);
    CHECK(c.ok());  // inside the margin
    AngleCheck d;
    Hold(&d, true, kSteerLimitRad + 4.0f * kDeg, 300, &t);
    CHECK(!d.ok());
    AngleCheck e;
    Hold(&e, true, -(kSteerLimitRad + 4.0f * kDeg), 300, &t);
    CHECK(!e.ok());
  }
  {
    Test("angle: a jump of more than 3 deg in one tick -> fault (e.g. a wrap)");
    AngleCheck c;
    uint32_t t = 1000;
    Hold(&c, true, 0.0f, 300, &t);
    t += kTick;
    c.Update(true, 2.0f * kDeg, t);
    CHECK(c.ok());   // 2 deg in one tick: allowed
    t += kTick;
    c.Update(true, 6.0f * kDeg, t);
    CHECK(!c.ok());  // 4 deg in one tick: not
  }
  {
    Test("angle: NaN -> fault");
    AngleCheck c;
    uint32_t t = 1000;
    Hold(&c, true, 0.0f, 300, &t);
    t += kTick;
    c.Update(true, NAN, t);
    CHECK(!c.ok());
  }
  {
    Test("angle: trust clears correctly across the micros() wrap");
    AngleCheck c;
    uint32_t t = 0xFFFFFFFFu - 50000u;  // wraps 50 ms in
    Hold(&c, true, 0.0f, 250, &t);
    CHECK(c.ok());
  }
  {
    Test("wheel: 1 rev/s -> one circumference per second; sign follows direction; still = 0");
    WheelSpeed w;
    uint32_t t = 1000;
    CHECK(Near(SpinWheel(&w, 1.0f, 1.0f, &t), kWheelCircumferenceM, 0.12f));
    WheelSpeed r;
    CHECK(Near(SpinWheel(&r, -0.5f, 1.0f, &t), -0.5f * kWheelCircumferenceM, 0.12f));
    WheelSpeed s;
    CHECK(SpinWheel(&s, 0.0f, 1.0f, &t) == 0.0f);
  }
  {
    Test("wheel: survives the micros() wrap");
    WheelSpeed w;
    uint32_t t = 0xFFFFFFFFu - 100000u;
    CHECK(Near(SpinWheel(&w, 1.0f, 1.0f, &t), kWheelCircumferenceM, 0.12f));
  }
  {
    Test("wheel: back to zero once the wheel stops (within the 200 ms window)");
    WheelSpeed w;
    uint32_t t = 1000;
    SpinWheel(&w, 1.0f, 1.0f, &t);
    CHECK(SpinWheel(&w, 0.0f, 0.3f, &t) == 0.0f);
  }

  printf("\n%d passed, %d failed\n", g_pass, g_fail);
  return g_fail == 0 ? 0 : 1;
}
