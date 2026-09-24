#!/bin/bash
set -e

source /opt/ros/humble/setup.bash
source /home/ubuntu/ros2_ws/install/setup.bash

unset RMW_IMPLEMENTATION
unset CYCLONEDDS_URI

rm -rf ~/.ros/log/* 2>/dev/null || true
ros2 daemon stop 2>/dev/null || true
sleep 2

case "${1:-sim}" in

    sim)
        exec ros2 launch xarm_planner xarm7_planner_fake.launch.py
        ;;

    real)
        exec ros2 launch xarm_planner xarm7_planner_realmove.launch.py \
            robot_ip:="$2"
        ;;

    *)
        exec "$@"
        ;;
esac