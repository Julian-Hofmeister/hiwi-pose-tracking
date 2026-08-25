#!/bin/bash
set -eo pipefail

# ROS setup.bash uses unset variables; do not enable nounset here.
source /opt/ros/jazzy/setup.bash

if [ -f /ws/install/setup.bash ]; then
  source /ws/install/setup.bash
fi

exec "$@"
