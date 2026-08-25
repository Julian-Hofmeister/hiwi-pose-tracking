#!/bin/bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
cd /ws

colcon build --symlink-install --packages-up-to rtmpose_ros
source /ws/install/setup.bash

colcon test --packages-select rtmpose_ros --event-handlers console_direct+
colcon test-result --all --verbose
