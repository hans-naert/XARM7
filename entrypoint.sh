#!/bin/bash
set -e

source /opt/ros/humble/setup.bash
source /home/ubuntu/ros2_ws/install/setup.bash

# Use FastDDS (default) - more stable in Docker than CycloneDDS
unset RMW_IMPLEMENTATION
unset CYCLONEDDS_URI

rm -rf ~/.ros/log/* 2>/dev/null || true
ros2 daemon stop 2>/dev/null || true
sleep 2

if [ "$#" -eq 0 ]; then
    exec ros2 launch xarm_planner xarm7_planner_fake.launch.py
else
    exec "$@"
fi
