// Copyright 2026 MRider contributors
// SPDX-License-Identifier: Apache-2.0
//
// uros_echo -- micro-ROS + mitt_msgs smoke test. DRIVES NO PINS.
//
// Flash this BEFORE mitt_dbw, with nothing wired to the Teensy but USB and the logic rail.
// It separates "the toolchain / agent / custom message build is broken" from "the DBW firmware
// is broken", which otherwise look identical: no /mitt/dbw/status.
//
//   pio run -e uros_echo -t upload
//   ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/mitt_dbw -b 115200
//   ros2 topic hz /mitt/dbw/status                                    # ~50 Hz
//   ros2 topic pub -r 50 /mitt/dbw/command mitt_msgs/msg/DbwCommand "{steering_angle: 0.1, speed: 0.0}"
//   ros2 topic echo /mitt/dbw/status --field steering_setpoint         # echoes 0.1
//
// mode is always ESTOP, drive_ticks counts published messages, steering_setpoint echoes the
// last DbwCommand.steering_angle, and faults = FAULT_SETPOINT_STALE until a command arrives.

#include <Arduino.h>
#include <string.h>

#if defined(MICRO_ROS_TRANSPORT_ARDUINO_SERIAL)
#include <micro_ros_platformio.h>
#else
#include <micro_ros_arduino.h>
#endif

#include <rcl/rcl.h>
#include <rclc/executor.h>
#include <rclc/rclc.h>
#include <rmw_microros/rmw_microros.h>

#include <mitt_msgs/msg/dbw_command.h>
#include <mitt_msgs/msg/dbw_status.h>

namespace {

// GCC ignores a (void) cast on warn_unused_result functions; this does not.
#define MITT_IGNORE(expr) \
  do {                    \
    auto mitt_ret_ = (expr); \
    (void)mitt_ret_;      \
  } while (0)

rcl_allocator_t g_alloc;
rclc_support_t g_support;
rcl_node_t g_node;
rcl_publisher_t g_pub;
rcl_subscription_t g_sub;
rclc_executor_t g_exec;
mitt_msgs__msg__DbwCommand g_cmd;
mitt_msgs__msg__DbwStatus g_status;
bool g_connected = false;
bool g_have_cmd = false;
uint32_t g_last_cmd_ms = 0;
uint32_t g_last_pub_ms = 0;
uint32_t g_last_ping_ms = 0;

void OnCommand(const void* msgin) {
  const auto* m = static_cast<const mitt_msgs__msg__DbwCommand*>(msgin);
  g_status.steering_setpoint = m->steering_angle;
  g_status.wheel_speed = m->speed;  // echo, so both fields of the command are visible
  g_have_cmd = true;
  g_last_cmd_ms = millis();
}

bool Create() {
  g_alloc = rcl_get_default_allocator();
  if (rclc_support_init(&g_support, 0, NULL, &g_alloc) != RCL_RET_OK) return false;
  if (rclc_node_init_default(&g_node, "mitt_dbw", "", &g_support) != RCL_RET_OK) return false;
  if (rclc_publisher_init_best_effort(&g_pub, &g_node,
                                      ROSIDL_GET_MSG_TYPE_SUPPORT(mitt_msgs, msg, DbwStatus),
                                      "/mitt/dbw/status") != RCL_RET_OK)
    return false;
  if (rclc_subscription_init_best_effort(&g_sub, &g_node,
                                         ROSIDL_GET_MSG_TYPE_SUPPORT(mitt_msgs, msg, DbwCommand),
                                         "/mitt/dbw/command") != RCL_RET_OK)
    return false;
  g_exec = rclc_executor_get_zero_initialized_executor();
  if (rclc_executor_init(&g_exec, &g_support.context, 1, &g_alloc) != RCL_RET_OK) return false;
  if (rclc_executor_add_subscription(&g_exec, &g_sub, &g_cmd, &OnCommand, ON_NEW_DATA) !=
      RCL_RET_OK)
    return false;
  MITT_IGNORE(rmw_uros_sync_session(100));
  return true;
}

void Destroy() {
  rmw_context_t* ctx = rcl_context_get_rmw_context(&g_support.context);
  MITT_IGNORE(rmw_uros_set_context_entity_destroy_session_timeout(ctx, 0));
  MITT_IGNORE(rclc_executor_fini(&g_exec));
  MITT_IGNORE(rcl_subscription_fini(&g_sub, &g_node));
  MITT_IGNORE(rcl_publisher_fini(&g_pub, &g_node));
  MITT_IGNORE(rcl_node_fini(&g_node));
  MITT_IGNORE(rclc_support_fini(&g_support));
}

}  // namespace

void setup() {
#if defined(MICRO_ROS_TRANSPORT_ARDUINO_SERIAL)
  Serial.begin(115200);
  set_microros_serial_transports(Serial);
#else
  set_microros_transports();
#endif
  pinMode(LED_BUILTIN, OUTPUT);
  memset(&g_cmd, 0, sizeof(g_cmd));
  memset(&g_status, 0, sizeof(g_status));
}

void loop() {
  const uint32_t now = millis();

  if (!g_connected) {
    digitalWriteFast(LED_BUILTIN, (now / 500) & 1);  // slow blink: waiting for the agent
    if (now - g_last_ping_ms >= 500) {
      g_last_ping_ms = now;
      if (rmw_uros_ping_agent(50, 1) == RMW_RET_OK) {
        g_connected = Create();
        if (!g_connected) Destroy();
      }
    }
    return;
  }

  if (now - g_last_ping_ms >= 1000) {
    g_last_ping_ms = now;
    if (rmw_uros_ping_agent(50, 3) != RMW_RET_OK) {
      Destroy();
      g_connected = false;
      return;
    }
  }

  MITT_IGNORE(rclc_executor_spin_some(&g_exec, RCL_MS_TO_NS(0)));

  if (now - g_last_pub_ms >= 20) {  // 50 Hz
    g_last_pub_ms = now;
    const int64_t ns = rmw_uros_epoch_synchronized() ? rmw_uros_epoch_nanos()
                                                     : (int64_t)micros() * 1000LL;
    g_status.stamp.sec = (int32_t)(ns / 1000000000LL);
    g_status.stamp.nanosec = (uint32_t)(ns % 1000000000LL);
    g_status.mode = mitt_msgs__msg__DbwStatus__MODE_ESTOP;
    const bool stale = !g_have_cmd || (now - g_last_cmd_ms) > 500;
    g_status.faults = stale ? mitt_msgs__msg__DbwStatus__FAULT_SETPOINT_STALE : 0;
    g_status.drive_ticks += 1;
    MITT_IGNORE(rcl_publish(&g_pub, &g_status, NULL));
    digitalWriteFast(LED_BUILTIN, HIGH);  // solid: connected and publishing
  }
}
