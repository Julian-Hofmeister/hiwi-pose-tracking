"""Publish RGB frames from a synthetic pattern, image file, video, or webcam."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class ImageSourceNode(Node):
    """Mock camera that publishes ``sensor_msgs/Image`` on the relative topic ``image``."""

    def __init__(self) -> None:
        super().__init__('image_source')
        self.declare_parameter('source_type', 'synthetic')
        self.declare_parameter('path', '')
        self.declare_parameter('device_index', 0)
        self.declare_parameter('fps', 15.0)
        self.declare_parameter('frame_id', 'camera_optical_frame')
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)

        self._bridge = CvBridge()
        self._pub = self.create_publisher(Image, 'image', qos_profile_sensor_data)
        self._cap: cv2.VideoCapture | None = None
        self._still: np.ndarray | None = None
        self._frame_index = 0

        source_type = str(self.get_parameter('source_type').value)
        fps = float(self.get_parameter('fps').value)
        self._frame_id = str(self.get_parameter('frame_id').value)
        self._source_type = source_type.lower()

        self._setup_source()

        period = 1.0 / max(fps, 0.1)
        self._timer = self.create_timer(period, self._on_timer)
        self.get_logger().info(
            f'image_source ready ({self._source_type}) publishing relative topic "image" '
            f'at {fps:.1f} FPS, frame_id="{self._frame_id}".'
        )

    def _setup_source(self) -> None:
        path = str(self.get_parameter('path').value)
        device_index = int(self.get_parameter('device_index').value)
        width = int(self.get_parameter('width').value)
        height = int(self.get_parameter('height').value)

        if self._source_type == 'synthetic':
            self._width = max(width, 1)
            self._height = max(height, 1)
            return

        if self._source_type == 'image':
            if not path:
                raise RuntimeError('Parameter "path" is required for source_type=image')
            image = cv2.imread(path, cv2.IMREAD_COLOR)
            if image is None:
                raise RuntimeError(f'Could not read image file: {path}')
            self._image_path = path
            self._still = image
            return

        if self._source_type in ('video', 'webcam'):
            target = path if self._source_type == 'video' else device_index
            if self._source_type == 'video' and not path:
                raise RuntimeError('Parameter "path" is required for source_type=video')
            if self._source_type == 'video' and not Path(path).is_file():
                raise RuntimeError(f'Video file not found: {path}')
            self._cap = cv2.VideoCapture(target)
            if not self._cap.isOpened():
                raise RuntimeError(f'Could not open {self._source_type} source: {target}')
            return

        raise RuntimeError(
            f'Unknown source_type "{self._source_type}". '
            'Use synthetic, image, video, or webcam.'
        )

    def _next_frame(self) -> np.ndarray | None:
        if self._source_type == 'synthetic':
            return _synthetic_frame(self._width, self._height, self._frame_index)

        if self._source_type == 'image':
            image = cv2.imread(self._image_path, cv2.IMREAD_COLOR)
            return image if image is not None else self._still

        assert self._cap is not None
        ok, frame = self._cap.read()
        if ok:
            return frame
        if self._source_type == 'video':
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._cap.read()
            return frame if ok else None
        self.get_logger().warning('Webcam returned no frame')
        return None

    def _on_timer(self) -> None:
        frame = self._next_frame()
        self._frame_index += 1
        if frame is None:
            return

        msg = self._bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self._frame_id
        self._pub.publish(msg)

    def destroy_node(self) -> bool:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        return super().destroy_node()


def _synthetic_frame(width: int, height: int, index: int) -> np.ndarray:
    """Color bars plus a moving stripe so frames are visually distinct."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    bar_width = max(width // 3, 1)
    frame[:, :bar_width] = (0, 0, 180)
    frame[:, bar_width:2 * bar_width] = (0, 180, 0)
    frame[:, 2 * bar_width:] = (180, 0, 0)
    stripe = index % max(height, 1)
    frame[stripe:stripe + 4, :] = (255, 255, 255)
    return frame


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = ImageSourceNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as exc:  # noqa: BLE001 — fail startup with a clear log
        rclpy.logging.get_logger('image_source').error(str(exc))
        raise
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
