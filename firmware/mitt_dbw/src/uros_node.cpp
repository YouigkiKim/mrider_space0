// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0

#include "uros_node.h"

#include <Arduino.h>
#include <string.h>

#include <micro_ros_arduino.h>
#include <rcl/rcl.h>
#include <rclc/executor.h>
#include <rclc/rclc.h>
#include <rmw_microros/rmw_microros.h>

#include <mitt_msgs/msg/dbw_status.h>
#include <std_msgs/msg/float32_multi_array.h>
#include <std_srvs/srv/trigger.h>

#include "mitt_config.h"
#include "sensors.h"

// GCC ignores a (void) cast on warn_unused_result functions; this does not.
#define MITT_IGNORE(expr)    \
  do {                       \
    auto mitt_ret_ = (expr); \
    (void)mitt_ret_;         \
  } while (0)

// The firmware's numbers must be the .msg constants, or the laptop decodes a different state.
static_assert(mitt_msgs__msg__DbwStatus__MODE_ESTOP == 0, "MODE_ESTOP");
static_assert(mitt_msgs__msg__DbwStatus__FAULT_ENCODER == mitt::kFaultEncoder, "FAULT_ENCODER");

// micro_ros_arduino's default arduino_transport_open() calls Serial.begin(), which on Teensy 4
// blocks up to 2 s waiting for the host to open the port. rmw_uros_ping_agent() opens the
// transport on every ping, so with USB plugged in and no agent running the loop stalls past the
// 250 ms watchdog and the board resets every few seconds. USB CDC on Teensy needs no begin().
extern "C" bool arduino_transport_open(struct uxrCustomTransport* /*transport*/) { return true; }

namespace mitt {
namespace uros {
namespace {

enum class LinkState { kWaitingAgent, kConnected };

constexpr size_t kDebugLen = 5;
constexpr size_t kHandles = 1;  // the zero service

ZeroHandler g_zero = nullptr;
LinkState g_state = LinkState::kWaitingAgent;
uint32_t g_last_ping_ms = 0;
uint32_t g_last_sync_ms = 0;
uint8_t g_ping_fails = 0;

rcl_allocator_t g_allocator;
rclc_support_t g_support;
rcl_node_t g_node;
rcl_publisher_t g_status_pub;
rcl_publisher_t g_debug_pub;
rcl_service_t g_zero_srv;
rclc_executor_t g_executor;

bool g_support_ok = false, g_node_ok = false, g_pub_ok = false, g_dbg_ok = false,
     g_srv_ok = false, g_exec_ok = false;

mitt_msgs__msg__DbwStatus g_status_msg;
std_msgs__msg__Float32MultiArray g_debug_msg;
float g_debug_data[kDebugLen];
std_srvs__srv__Trigger_Request g_zero_req;
std_srvs__srv__Trigger_Response g_zero_res;
char g_zero_text[96];

void OnZero(const void* /*req*/, void* res_v) {
  auto* res = static_cast<std_srvs__srv__Trigger_Response*>(res_v);
  bool ok = false;
  if (g_zero) {
    ok = g_zero(g_zero_text, sizeof(g_zero_text));
  } else {
    strncpy(g_zero_text, "no handler", sizeof(g_zero_text));
  }
  g_zero_text[sizeof(g_zero_text) - 1] = '\0';
  res->success = ok;
  res->message.data = g_zero_text;
  res->message.size = strlen(g_zero_text);
  res->message.capacity = sizeof(g_zero_text);
}

void DestroyEntities() {
  if (g_support_ok) {
    rmw_context_t* ctx = rcl_context_get_rmw_context(&g_support.context);
    MITT_IGNORE(rmw_uros_set_context_entity_destroy_session_timeout(ctx, 0));  // agent may be gone
  }
  if (g_exec_ok) MITT_IGNORE(rclc_executor_fini(&g_executor));
  if (g_srv_ok) MITT_IGNORE(rcl_service_fini(&g_zero_srv, &g_node));
  if (g_dbg_ok) MITT_IGNORE(rcl_publisher_fini(&g_debug_pub, &g_node));
  if (g_pub_ok) MITT_IGNORE(rcl_publisher_fini(&g_status_pub, &g_node));
  if (g_node_ok) MITT_IGNORE(rcl_node_fini(&g_node));
  if (g_support_ok) MITT_IGNORE(rclc_support_fini(&g_support));
  g_support_ok = g_node_ok = g_pub_ok = g_dbg_ok = g_srv_ok = g_exec_ok = false;
}

bool CreateEntities(void (*between)()) {
  g_allocator = rcl_get_default_allocator();

  if (rclc_support_init(&g_support, 0, NULL, &g_allocator) != RCL_RET_OK) return false;
  g_support_ok = true;
  between();
  // Bound every later creation round-trip (default 1000 ms) well under the watchdog.
  MITT_IGNORE(rmw_uros_set_context_entity_creation_session_timeout(
      rcl_context_get_rmw_context(&g_support.context), kEntityTimeoutMs));

  if (rclc_node_init_default(&g_node, kNodeName, "", &g_support) != RCL_RET_OK) return false;
  g_node_ok = true;
  between();

  if (rclc_publisher_init_best_effort(&g_status_pub, &g_node,
                                      ROSIDL_GET_MSG_TYPE_SUPPORT(mitt_msgs, msg, DbwStatus),
                                      kTopicStatus) != RCL_RET_OK)
    return false;
  g_pub_ok = true;
  between();

  if (rclc_publisher_init_best_effort(&g_debug_pub, &g_node,
                                      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32MultiArray),
                                      kTopicDebug) != RCL_RET_OK)
    return false;
  g_dbg_ok = true;
  between();

  if (rclc_service_init_default(&g_zero_srv, &g_node,
                                ROSIDL_GET_SRV_TYPE_SUPPORT(std_srvs, srv, Trigger),
                                kServiceZero) != RCL_RET_OK)
    return false;
  g_srv_ok = true;
  between();

  g_executor = rclc_executor_get_zero_initialized_executor();
  if (rclc_executor_init(&g_executor, &g_support.context, kHandles, &g_allocator) != RCL_RET_OK)
    return false;
  g_exec_ok = true;
  if (rclc_executor_add_service(&g_executor, &g_zero_srv, &g_zero_req, &g_zero_res, &OnZero) !=
      RCL_RET_OK)
    return false;

  // Session time sync: DbwStatus.stamp becomes laptop-referenced (calibration.md §6).
  MITT_IGNORE(rmw_uros_sync_session(kTimeSyncTimeoutMs));
  g_last_sync_ms = millis();
  between();
  return true;
}

void FillStamp(builtin_interfaces__msg__Time* t, uint32_t sample_us) {
  int64_t ns;
  if (rmw_uros_epoch_synchronized()) {
    ns = rmw_uros_epoch_nanos() - (int64_t)(uint32_t)(micros() - sample_us) * 1000LL;
  } else {
    ns = (int64_t)sample_us * 1000LL;  // not synced yet: time since boot (wraps at 71 min)
  }
  if (ns < 0) ns = 0;
  t->sec = (int32_t)(ns / 1000000000LL);
  t->nanosec = (uint32_t)(ns % 1000000000LL);
}

}  // namespace

void Begin(ZeroHandler zero) {
  g_zero = zero;
  memset(&g_status_msg, 0, sizeof(g_status_msg));
  memset(&g_debug_msg, 0, sizeof(g_debug_msg));
  g_debug_msg.data.data = g_debug_data;
  g_debug_msg.data.size = kDebugLen;
  g_debug_msg.data.capacity = kDebugLen;
  memset(&g_zero_req, 0, sizeof(g_zero_req));
  memset(&g_zero_res, 0, sizeof(g_zero_res));
  set_microros_transports();
  g_state = LinkState::kWaitingAgent;
}

bool Connected() { return g_state == LinkState::kConnected; }

void Spin(void (*between)()) {
  const uint32_t now = millis();
  switch (g_state) {
    case LinkState::kWaitingAgent:
      if ((uint32_t)(now - g_last_ping_ms) >= 500u) {
        g_last_ping_ms = now;
        if (rmw_uros_ping_agent(kAgentPingTimeoutMs, 1) == RMW_RET_OK) {
          between();
          if (CreateEntities(between)) {
            g_state = LinkState::kConnected;
            g_ping_fails = 0;
            g_last_ping_ms = millis();
          } else {
            DestroyEntities();
          }
        }
      }
      break;

    case LinkState::kConnected:
      if ((uint32_t)(now - g_last_ping_ms) >= kAgentPingPeriodMs) {
        g_last_ping_ms = now;
        if (rmw_uros_ping_agent(kAgentPingTimeoutMs, 1) == RMW_RET_OK) {
          g_ping_fails = 0;
        } else if (++g_ping_fails >= kAgentPingFailLimit) {
          DestroyEntities();  // session gone; rebuild when the agent returns
          g_state = LinkState::kWaitingAgent;
          break;
        }
        between();
      }
      if ((uint32_t)(now - g_last_sync_ms) >= kTimeSyncPeriodMs) {
        g_last_sync_ms = now;
        MITT_IGNORE(rmw_uros_sync_session(kTimeSyncTimeoutMs));
        between();
      }
      MITT_IGNORE(rclc_executor_spin_some(&g_executor, RCL_MS_TO_NS(0)));
      break;
  }
}

void Publish(const Sample& s, uint32_t sample_us) {
  if (g_state != LinkState::kConnected) return;
  FillStamp(&g_status_msg.stamp, sample_us);
  g_status_msg.steering_angle = s.steering_angle;
  g_status_msg.steering_setpoint = 0.0f;  // nothing is commanded in this build
  g_status_msg.wheel_speed = s.wheel_speed;
  g_status_msg.drive_ticks = s.drive_ticks;
  g_status_msg.mode = mitt_msgs__msg__DbwStatus__MODE_ESTOP;
  g_status_msg.faults = s.faults;
  MITT_IGNORE(rcl_publish(&g_status_pub, &g_status_msg, NULL));

  g_debug_data[0] = (float)s.raw;
  g_debug_data[1] = s.i2c_ok ? 1.0f : 0.0f;
  g_debug_data[2] = s.magnet_ok ? 1.0f : 0.0f;
  g_debug_data[3] = (float)s.c0;
  g_debug_data[4] = s.wdt_reset ? 1.0f : 0.0f;
  MITT_IGNORE(rcl_publish(&g_debug_pub, &g_debug_msg, NULL));
}

}  // namespace uros
}  // namespace mitt
