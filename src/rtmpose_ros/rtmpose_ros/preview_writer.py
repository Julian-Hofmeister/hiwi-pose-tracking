"""Write the latest ``debug_image`` to a JPEG so you can view it on the host."""

from __future__ import annotations

import time
from pathlib import Path

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class PreviewWriterNode(Node):
    def __init__(self) -> None:
        super().__init__('preview_writer')
        self.declare_parameter('output_path', '/ws/tmp/live_preview.jpg')
        self._path = Path(str(self.get_parameter('output_path').value))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._bridge = CvBridge()
        self.create_subscription(
            Image, 'debug_image', self._on_image, qos_profile_sensor_data
        )
        self.get_logger().info(f'writing debug overlay to {self._path.parent}/live_preview.*.jpg')

    def _on_image(self, msg: Image) -> None:
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f'preview convert failed: {exc}')
            return
        ok, encoded = cv2.imencode('.jpg', frame)
        if not ok:
            return
        self._write_jpeg(encoded.tobytes())

    def _write_jpeg(self, data: bytes) -> None:
        """Write a new file each frame so Windows readers never lock the writer."""
        frame_path = self._path.parent / f'live_preview.{time.time_ns()}.jpg'
        try:
            frame_path.write_bytes(data)
        except OSError as exc:
            self.get_logger().warning(f'preview write failed: {exc}', throttle_duration_sec=2.0)
            return
        # Keep a small ring of frames; delete older ones.
        frames = sorted(self._path.parent.glob('live_preview.*.jpg'))
        for old in frames[:-3]:
            try:
                old.unlink(missing_ok=True)
            except OSError:
                pass


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = PreviewWriterNode()
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
