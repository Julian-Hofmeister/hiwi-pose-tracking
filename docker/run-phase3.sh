#!/bin/bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
cd /ws

colcon build --symlink-install --packages-up-to rtmpose_ros
source /ws/install/setup.bash

echo "=== colcon test (ROS process uses mock / subprocess mock, not MMPose) ==="
colcon test --packages-select rtmpose_ros --event-handlers console_direct+
colcon test-result --all --verbose

VENV="${RTMPOSE_VENV:-/opt/rtmpose}"
TEST_IMAGE="${RTMPOSE_TEST_IMAGE:-/tmp/rtmpose_coco_785.jpg}"
COCO_URL="https://raw.githubusercontent.com/open-mmlab/mmpose/main/tests/data/coco/000000000785.jpg"

if [ ! -x "$VENV/bin/python" ]; then
  echo "MMPose venv not found at $VENV" >&2
  exit 1
fi

if [ ! -f "$TEST_IMAGE" ]; then
  wget -q -O "$TEST_IMAGE" "$COCO_URL"
fi

echo "=== subprocess RTMPose worker smoke ==="
RTMPOSE_TEST_IMAGE="$TEST_IMAGE" RTMPOSE_VENV="$VENV" python3 - <<'PY'
import os
import time
from pathlib import Path

import cv2

from rtmpose_ros.estimator_bridge import SubprocessPoseEstimator
from rtmpose_ros.inference import PoseEstimatorConfig

image_path = Path(os.environ['RTMPOSE_TEST_IMAGE'])
image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
assert image is not None, f'missing test image at {image_path}'
python_exe = str(Path(os.environ['RTMPOSE_VENV']) / 'bin' / 'python')

started = time.monotonic()
estimator = SubprocessPoseEstimator(
    PoseEstimatorConfig(backend='rtmpose', device='cpu', pose_model='human'),
    python_executable=python_exe,
)
loaded = time.monotonic()
first = estimator.estimate(image)
after_first = time.monotonic()
second = estimator.estimate(image)
after_second = time.monotonic()
estimator.close()

print(
    f'model={first.model_name} size={first.image_width}x{first.image_height} '
    f'persons={len(first.poses)} keypoints={len(first.poses[0].keypoints) if first.poses else 0}'
)
print(
    f'load={(loaded - started) * 1000:.0f}ms '
    f'infer1={(after_first - loaded) * 1000:.0f}ms '
    f'infer2={(after_second - after_first) * 1000:.0f}ms'
)
assert first.poses, 'expected at least one person on the COCO sample'
assert second.poses, 'second inference on the same worker must keep working'
print('subprocess rtmpose worker ok')
PY

echo "=== ROS node + RTMPose worker smoke ==="
RTMPOSE_TEST_IMAGE="$TEST_IMAGE" python3 - <<'PY'
import os
import time
from pathlib import Path

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from rtmpose_ros.node import PoseEstimatorNode

image = cv2.imread(os.environ['RTMPOSE_TEST_IMAGE'], cv2.IMREAD_COLOR)
assert image is not None

rclpy.init()
node = PoseEstimatorNode()
assert node._estimator is not None, 'RTMPose worker failed to start'

bridge = CvBridge()
helper = rclpy.create_node('phase3_smoke_helper')
publisher = helper.create_publisher(Image, 'image', qos_profile_sensor_data)
received: list[Image] = []
helper.create_subscription(
    Image, 'debug_image', received.append, qos_profile_sensor_data
)
executor = SingleThreadedExecutor()
executor.add_node(node)
executor.add_node(helper)

outgoing = bridge.cv2_to_imgmsg(image, encoding='bgr8')
outgoing.header.stamp.sec = 7
outgoing.header.frame_id = 'phase3_camera'

deadline = time.monotonic() + 90.0
while time.monotonic() < deadline and publisher.get_subscription_count() < 1:
    executor.spin_once(timeout_sec=0.1)

assert publisher.get_subscription_count() >= 1, 'node did not subscribe to image'

while time.monotonic() < deadline and not received:
    publisher.publish(outgoing)
    executor.spin_once(timeout_sec=0.1)

node.destroy_node()
helper.destroy_node()
executor.shutdown()
if rclpy.ok():
    rclpy.shutdown()

assert received, 'no debug_image from RTMPose node'
result = received[0]
assert result.header.frame_id == 'phase3_camera'
assert result.header.stamp.sec == 7
assert result.encoding == 'bgr8'
assert result.width == image.shape[1]
assert result.height == image.shape[0]
print(f'ros+rtmpose ok, debug {result.width}x{result.height}')
PY
