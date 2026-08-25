#!/bin/bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
cd /ws

colcon build --symlink-install --packages-up-to rtmpose_ros
source /ws/install/setup.bash

echo "=== colcon test ==="
colcon test --packages-select human_pose_msgs rtmpose_ros --event-handlers console_direct+
colcon test-result --all --verbose

mkdir -p /ws/tmp
TEST_IMAGE="${RTMPOSE_TEST_IMAGE:-/tmp/rtmpose_coco_785.jpg}"
if [ ! -f "$TEST_IMAGE" ]; then
  wget -q -O "$TEST_IMAGE" https://raw.githubusercontent.com/open-mmlab/mmpose/main/tests/data/coco/000000000785.jpg
fi

echo "=== runtime mock 640x480 @ 15 FPS ==="
python3 /ws/scripts/measure_runtime.py \
  --backend mock \
  --seconds 4 \
  --fps 15 \
  --width 640 \
  --height 480 \
  --output /ws/tmp/metrics_mock.json

echo "=== runtime RTMPose CPU on COCO sample ==="
python3 /ws/scripts/measure_runtime.py \
  --backend rtmpose \
  --device cpu \
  --seconds 8 \
  --fps 5 \
  --image "$TEST_IMAGE" \
  --output /ws/tmp/metrics_rtmpose.json

echo "=== instance memory ==="
python3 /ws/scripts/report_instance_memory.py

echo "=== metrics ==="
python3 - <<'PY'
import json
from pathlib import Path
for name in ("metrics_mock.json", "metrics_rtmpose.json"):
    path = Path("/ws/tmp") / name
    print(name)
    print(path.read_text(encoding="utf-8"))
PY
