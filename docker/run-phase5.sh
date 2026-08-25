#!/bin/bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
cd /ws

colcon build --symlink-install --packages-up-to rtmpose_ros
source /ws/install/setup.bash

echo "=== colcon test ==="
colcon test --packages-select human_pose_msgs rtmpose_ros --event-handlers console_direct+
colcon test-result --all --verbose

echo "=== multi-camera launch smoke (mock backend, no MMPose) ==="
python3 - <<'PY'
import os
import signal
import subprocess
import time

proc = subprocess.Popen(
    [
        'ros2', 'launch', 'rtmpose_ros', 'multi_camera.launch.py',
        'backend:=mock',
        'fps:=2.0',
    ],
    start_new_session=True,
)
try:
    deadline = time.monotonic() + 15.0
    nodes = ''
    while time.monotonic() < deadline:
        listed = subprocess.run(
            ['ros2', 'node', 'list'],
            check=False,
            capture_output=True,
            text=True,
        )
        nodes = listed.stdout or ''
        if (
            '/camera_1/pose_estimator' in nodes
            and '/camera_2/pose_estimator' in nodes
            and '/webcam/pose_estimator' in nodes
        ):
            break
        time.sleep(0.5)
    topics = subprocess.run(
        ['ros2', 'topic', 'list'],
        check=False,
        capture_output=True,
        text=True,
    ).stdout
    print('nodes:\n', nodes)
    print('topics:\n', topics)
    for name in (
        '/camera_1/pose_estimator',
        '/camera_2/pose_estimator',
        '/webcam/pose_estimator',
        '/camera_1/image_source',
        '/camera_2/image_source',
        '/webcam/image_source',
    ):
        assert name in nodes, f'missing node {name}'
    for name in (
        '/camera_1/image',
        '/camera_1/poses',
        '/camera_2/image',
        '/camera_2/poses',
        '/webcam/image',
        '/webcam/poses',
    ):
        assert name in topics, f'missing topic {name}'
    print('multi-camera launch smoke ok')
    print('=== instance memory while 3 mock instances are up ===')
    subprocess.run(['python3', '/ws/scripts/report_instance_memory.py'], check=False)
finally:
    try:
        os.killpg(proc.pid, signal.SIGINT)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)
PY

echo "=== instance memory (GPU if present) ==="
python3 /ws/scripts/report_instance_memory.py
