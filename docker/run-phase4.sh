#!/bin/bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
cd /ws

colcon build --symlink-install --packages-up-to rtmpose_ros
source /ws/install/setup.bash

echo "=== interface types ==="
ros2 interface show human_pose_msgs/msg/PersonPose2DArray
ros2 interface show human_pose_msgs/msg/PersonPose2D
ros2 interface show human_pose_msgs/msg/Keypoint2D

echo "=== colcon test ==="
colcon test --packages-select human_pose_msgs rtmpose_ros --event-handlers console_direct+
colcon test-result --all --verbose
