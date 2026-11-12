#!/usr/bin/env bash
# Rebuild lib/micro_ros_arduino -- the micro-ROS static library the firmware links against.
#
#   cd firmware/mitt_dbw && ./scripts/build_microros_lib.sh        (needs docker, ~5 min)
#
# What it builds (dbw.md §9 / software.md §6.3 version pinning):
#   micro_ros_arduino  v2.0.8-humble (commit below), target teensy4 (Teensy 4.x, imxrt1062)
#   + mitt_msgs        copied from ros2_ws/src/mitt_msgs  (custom messages must be compiled IN)
#   + microros/colcon.meta  stock meta with RMW_UXRCE_MAX_SERVICES 1 -> 6
#                           (5 for the ROS 2 parameter server + /mitt/dbw/zero_steering)
#   builder image pinned by digest.
#
# Re-run it whenever ros2_ws/src/mitt_msgs or microros/colcon.meta changes. The output is a
# build artifact (git-ignored); BUILD_INFO.txt inside it records exactly what went in.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"   # firmware/mitt_dbw
REPO="$(cd "$HERE/../.." && pwd)"
TAG="v2.0.8-humble"
COMMIT="8d527c414ea4264beaa032dedc0ccf7b6516013a"
IMAGE="microros/micro_ros_static_library_builder@sha256:0d2390805bd9da7f1dd9687e71747c6a010a9f9bdfc9de298eec0d25c96506b0"
OUT="$HERE/lib/micro_ros_arduino"

command -v docker >/dev/null || { echo "docker not found (sudo apt install docker.io)"; exit 1; }
docker info >/dev/null 2>&1 || { echo "docker not usable: is your user in the docker group? (newgrp docker)"; exit 1; }

WORK="$(mktemp -d)"
SRC="$WORK/micro_ros_arduino"
cleanup() {
  # the builder writes as root; hand everything back before deleting
  [ -d "$SRC" ] && docker run --rm -v "$SRC":/project --entrypoint chown "$IMAGE" \
      -R "$(id -u):$(id -g)" /project >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

echo "== clone micro_ros_arduino $TAG"
git clone -q --depth 1 -b "$TAG" https://github.com/micro-ROS/micro_ros_arduino.git "$SRC"
[ "$(git -C "$SRC" rev-parse HEAD)" = "$COMMIT" ] || { echo "tag $TAG moved: expected $COMMIT"; exit 1; }

echo "== add mitt_msgs, custom colcon.meta"
cp -r "$REPO/ros2_ws/src/mitt_msgs" "$SRC/extras/library_generation/extra_packages/"
cp "$HERE/microros/colcon.meta" "$SRC/extras/library_generation/colcon.meta"

echo "== build (teensy4)"
docker run --rm -v "$SRC":/project --env MICROROS_LIBRARY_FOLDER=extras "$IMAGE" -p teensy4
docker run --rm -v "$SRC":/project --entrypoint chown "$IMAGE" -R "$(id -u):$(id -g)" /project

[ -f "$SRC/src/imxrt1062/fpv5-d16-hard/libmicroros.a" ] || { echo "build produced no library"; exit 1; }
[ -f "$SRC/src/mitt_msgs/msg/dbw_status.h" ] || { echo "mitt_msgs missing from the build"; exit 1; }

echo "== install to lib/micro_ros_arduino"
rm -rf "$OUT"
mkdir -p "$HERE/lib"
rsync -a --exclude .git --exclude extras --exclude examples --exclude .github "$SRC/" "$OUT/"
{
  echo "micro_ros_arduino $TAG @ $COMMIT, target teensy4"
  echo "builder $IMAGE"
  echo "colcon.meta sha256 $(sha256sum "$HERE/microros/colcon.meta" | cut -d' ' -f1)"
  echo "mitt_msgs from ros2_ws/src/mitt_msgs @ repo commit $(git -C "$REPO" rev-parse --short HEAD)$(git -C "$REPO" diff --quiet -- ros2_ws/src/mitt_msgs || echo ' (+uncommitted changes)')"
  echo "built $(date -Iseconds) on $(hostname)"
} > "$OUT/BUILD_INFO.txt"
cat "$OUT/BUILD_INFO.txt"
echo "== done. Now: pio run -e mitt_dbw"
