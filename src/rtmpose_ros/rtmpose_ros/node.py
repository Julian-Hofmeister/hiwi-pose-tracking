"""ROS2 node: camera image → pose estimator → poses + debug overlay.

RTMPose runs in a separate Python process (``/opt/rtmpose``) so ROS and MMPose
do not share an interpreter. Incoming frames use latest-frame-wins.
"""

from __future__ import annotations

import threading
import time
from collections import deque

import rclpy
from cv_bridge import CvBridge
from human_pose_msgs.msg import PersonPose2DArray
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from rtmpose_ros.estimator_bridge import SubprocessPoseEstimator
from rtmpose_ros.frame_slot import LatestFrameSlot
from rtmpose_ros.inference import PoseEstimator, PoseEstimatorConfig, create_estimator
from rtmpose_ros.message_converter import result_to_pose_array
from rtmpose_ros.passthrough import copy_header
from rtmpose_ros.visualization import draw_poses


class PoseEstimatorNode(Node):
    """Subscribe to ``image`` and publish ``poses`` plus a ``debug_image`` overlay."""

    def __init__(self, estimator: PoseEstimator | None = None, **kwargs) -> None:
        super().__init__('pose_estimator', **kwargs)
        self._declare_parameters()

        self._bridge = CvBridge()
        self._slot: LatestFrameSlot[tuple] = LatestFrameSlot()
        self._stop = threading.Event()
        self._estimator: PoseEstimator | None = estimator
        self._owns_estimator = estimator is None
        self._worker: threading.Thread | None = None
        self._last_log = 0.0
        self._stats_lock = threading.Lock()
        self._frames_received = 0
        self._frames_inferred = 0
        self._poses_published = 0
        self._debug_published = 0
        self._infer_ms: deque[float] = deque(maxlen=256)

        if self._estimator is None:
            self._estimator = self._build_estimator()

        self._image_sub = self.create_subscription(
            Image,
            'image',
            self._on_image,
            qos_profile_sensor_data,
        )
        self._debug_pub = self.create_publisher(
            Image,
            'debug_image',
            qos_profile_sensor_data,
        )
        self._poses_pub = self.create_publisher(
            PersonPose2DArray,
            'poses',
            qos_profile_sensor_data,
        )

        if self._estimator is not None:
            self._worker = threading.Thread(target=self._inference_loop, name='pose_infer', daemon=True)
            self._worker.start()
            self.get_logger().info(
                'pose_estimator ready '
                f'(backend={self._string_param("backend")}, device={self._string_param("device")}).'
            )
        else:
            self.get_logger().error(
                'pose_estimator is running without an estimator; incoming images are dropped.'
            )

    def snapshot_stats(self) -> dict:
        """Counters for benchmarks. Safe to call from another thread."""
        with self._stats_lock:
            times = list(self._infer_ms)
            received = self._frames_received
            inferred = self._frames_inferred
            poses = self._poses_published
            debug = self._debug_published
            dropped = self._slot.dropped
        times.sort()
        return {
            'frames_received': received,
            'frames_inferred': inferred,
            'poses_published': poses,
            'debug_published': debug,
            'dropped_frames': dropped,
            'infer_ms_mean': _mean(times),
            'infer_ms_p50': _percentile(times, 0.50),
            'infer_ms_p95': _percentile(times, 0.95),
        }

    def _declare_parameters(self) -> None:
        self.declare_parameter('backend', 'rtmpose')
        self.declare_parameter('device', 'cpu')
        self.declare_parameter('pose_model', 'human')
        self.declare_parameter('pose_weights', '')
        self.declare_parameter('detector_model', '')
        self.declare_parameter('detector_weights', '')
        self.declare_parameter('keypoint_threshold', 0.3)
        self.declare_parameter('detection_threshold', 0.5)
        self.declare_parameter('publish_debug_image', True)
        self.declare_parameter('publish_poses', True)
        self.declare_parameter('rtmpose_python', '/opt/rtmpose/bin/python')

    def _string_param(self, name: str) -> str:
        return str(self.get_parameter(name).value)

    def _build_estimator(self) -> PoseEstimator | None:
        config = PoseEstimatorConfig(
            backend=self._string_param('backend'),
            device=self._string_param('device'),
            pose_model=self._string_param('pose_model'),
            pose_weights=self._string_param('pose_weights'),
            detector_model=self._string_param('detector_model'),
            detector_weights=self._string_param('detector_weights'),
            keypoint_threshold=float(self.get_parameter('keypoint_threshold').value),
            detection_threshold=float(self.get_parameter('detection_threshold').value),
        )
        try:
            if config.backend.strip().lower() == 'rtmpose':
                python_exe = self._string_param('rtmpose_python')
                return SubprocessPoseEstimator(config, python_executable=python_exe)
            return create_estimator(config)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f'Failed to start pose estimator: {exc}')
            return None

    def _on_image(self, msg: Image) -> None:
        try:
            cv_image = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f'Invalid image: {exc}')
            return
        with self._stats_lock:
            self._frames_received += 1
        self._slot.put((cv_image, msg))

    def _inference_loop(self) -> None:
        while not self._stop.is_set():
            item = self._slot.take(timeout=0.1)
            if item is None or self._estimator is None:
                continue
            cv_image, msg = item
            started = time.monotonic()
            try:
                result = self._estimator.estimate(cv_image)
            except Exception as exc:  # noqa: BLE001
                self.get_logger().error(f'Inference failed: {exc}')
                continue
            elapsed_ms = (time.monotonic() - started) * 1000.0
            with self._stats_lock:
                self._frames_inferred += 1
                self._infer_ms.append(elapsed_ms)
            self._log_result(result, elapsed_ms)
            if bool(self.get_parameter('publish_poses').value):
                try:
                    pose_msg = result_to_pose_array(result, msg.header)
                    self._poses_pub.publish(pose_msg)
                    with self._stats_lock:
                        self._poses_published += 1
                except Exception as exc:  # noqa: BLE001
                    self.get_logger().error(f'Failed to publish poses: {exc}')
            if not bool(self.get_parameter('publish_debug_image').value):
                continue
            try:
                overlay = draw_poses(cv_image, result)
                out = self._bridge.cv2_to_imgmsg(overlay, encoding='bgr8')
                copy_header(msg, out)
                self._debug_pub.publish(out)
                with self._stats_lock:
                    self._debug_published += 1
            except Exception as exc:  # noqa: BLE001
                self.get_logger().error(f'Failed to publish debug image: {exc}')

    def _log_result(self, result, elapsed_ms: float) -> None:
        now = time.monotonic()
        if now - self._last_log < 1.0:
            return
        self._last_log = now
        self.get_logger().info(
            f'{len(result.poses)} person(s), infer={elapsed_ms:.0f}ms, '
            f'dropped_frames={self._slot.dropped}, model={result.model_name}'
        )

    def destroy_node(self) -> bool:
        self._stop.set()
        worker = self._worker
        self._worker = None
        if worker is not None and worker.is_alive():
            worker.join(timeout=5.0)
        estimator = self._estimator
        self._estimator = None
        if self._owns_estimator and estimator is not None:
            close = getattr(estimator, 'close', None)
            if close is not None:
                try:
                    close()
                except Exception:  # noqa: BLE001
                    pass
        try:
            return super().destroy_node()
        except KeyboardInterrupt:
            return False


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _percentile(sorted_values: list[float], fraction: float) -> float | None:
    if not sorted_values:
        return None
    index = int(round(fraction * (len(sorted_values) - 1)))
    return sorted_values[index]


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = PoseEstimatorNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            try:
                node.destroy_node()
            except KeyboardInterrupt:
                pass
        if rclpy.ok():
            try:
                rclpy.shutdown()
            except KeyboardInterrupt:
                pass
