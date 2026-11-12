#!/usr/bin/env bash
# Build and run the host unit tests for the hardware-independent firmware logic.
#   cd firmware/mitt_dbw && ./test/host/run_host_tests.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

mkdir -p .host_build
g++ -std=c++17 -O1 -Wall -Wextra -Werror -Iinclude -Isrc \
    src/sensors.cpp test/host/test_sensors.cpp -o .host_build/test_sensors
./.host_build/test_sensors
