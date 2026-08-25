"""Measure pose-node throughput, latency, and dropped frames.

Run inside the ROS Docker workspace after sourcing install/setup.bash.
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from human_pose_msgs.msg import PersonPose2DArray
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from rtmpose_ros.inference import MockPoseEstimator, PoseEstimatorConfig
from rtmpose_ros.node import PoseEstimatorNode


def _load_image(path: str, width: int, height: int) -> np.ndarray:
    if path:
        image = cv2.imread(path, cv2.IMREAD_COLOR)
        if image is None:
            raise SystemExit(f'Could not read image: {path}')
        return image
    return np.full((height, width, 3), 40, dtype=np.uint8)


def _rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # Linux ru_maxrss is kilobytes.
    return usage.ru_maxrss / 1024.0


def measure(args: argparse.Namespace) -> dict:
    image = _load_image(args.image, args.width, args.height)
    height, width = image.shape[:2]
    period = 1.0 / max(args.fps, 0.1)

    rclpy.init()
    if args.backend == 'mock':
        node = PoseEstimatorNode(estimator=MockPoseEstimator(PoseEstimatorConfig(backend='mock')))
    else:
        node = PoseEstimatorNode(
            parameter_overrides=[
                Parameter('backend', Parameter.Type.STRING, 'rtmpose'),
                Parameter('device', Parameter.Type.STRING, args.device),
                Parameter('rtmpose_python', Parameter.Type.STRING, args.rtmpose_python),
            ]
        )
        if node._estimator is None:
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
            raise SystemExit('RTMPose worker failed to start')

    bridge = CvBridge()
    helper = rclpy.create_node('measure_helper')
    publisher = helper.create_publisher(Image, 'image', qos_profile_sensor_data)
    received: list[tuple[float, PersonPose2DArray]] = []
    helper.create_subscription(
        PersonPose2DArray,
        'poses',
        lambda msg: received.append((time.monotonic(), msg)),
        qos_profile_sensor_data,
    )
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    executor.add_node(helper)

    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline and publisher.get_subscription_count() < 1:
        executor.spin_once(timeout_sec=0.05)

    send_times: dict[int, float] = {}
    started = time.monotonic()
    end_at = started + args.seconds
    frame_index = 0
    next_send = started
    while time.monotonic() < end_at:
        now = time.monotonic()
        if now >= next_send:
            msg = bridge.cv2_to_imgmsg(image, encoding='bgr8')
            msg.header.stamp.sec = frame_index
            msg.header.stamp.nanosec = 0
            msg.header.frame_id = 'measure_camera'
            send_times[frame_index] = time.monotonic()
            publisher.publish(msg)
            frame_index += 1
            next_send += period
        executor.spin_once(timeout_sec=0.01)
    drain_until = time.monotonic() + 2.0
    while time.monotonic() < drain_until:
        executor.spin_once(timeout_sec=0.05)

    elapsed = max(time.monotonic() - started, 1e-6)
    stats = node.snapshot_stats()
    latencies = []
    for recv_at, pose_msg in received:
        sent = send_times.get(pose_msg.header.stamp.sec)
        if sent is not None:
            latencies.append((recv_at - sent) * 1000.0)

    payload = {
        'backend': args.backend,
        'device': args.device,
        'image_width': width,
        'image_height': height,
        'requested_fps': args.fps,
        'duration_s': round(elapsed, 3),
        'frames_sent': frame_index,
        'input_fps': round(frame_index / elapsed, 2),
        'output_fps': round(len(received) / elapsed, 2),
        'e2e_ms_mean': None if not latencies else round(sum(latencies) / len(latencies), 1),
        'e2e_ms_p95': None if not latencies else round(sorted(latencies)[int(0.95 * (len(latencies) - 1))], 1),
        'rss_mb': round(_rss_mb(), 1),
        **{
            key: (round(value, 1) if isinstance(value, float) else value)
            for key, value in stats.items()
        },
    }

    node.destroy_node()
    helper.destroy_node()
    executor.shutdown()
    if rclpy.ok():
        rclpy.shutdown()
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Measure pose estimator runtime.')
    parser.add_argument('--backend', choices=('mock', 'rtmpose'), default='mock')
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--seconds', type=float, default=5.0)
    parser.add_argument('--fps', type=float, default=15.0)
    parser.add_argument('--width', type=int, default=640)
    parser.add_argument('--height', type=int, default=480)
    parser.add_argument('--image', default='')
    parser.add_argument('--rtmpose-python', default=os.environ.get('RTMPOSE_VENV', '/opt/rtmpose') + '/bin/python')
    parser.add_argument('--output', default='')
    args = parser.parse_args(argv)

    payload = measure(args)
    text = json.dumps(payload, indent=2)
    if args.output:
        Path(args.output).write_text(text + '\n', encoding='utf-8')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
