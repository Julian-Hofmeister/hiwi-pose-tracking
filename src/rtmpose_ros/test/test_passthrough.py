from cv_bridge import CvBridge
from sensor_msgs.msg import Image
import numpy as np

from rtmpose_ros.passthrough import image_passthrough


def _make_bgr8_image(width: int = 32, height: int = 24) -> Image:
    pixels = np.zeros((height, width, 3), dtype=np.uint8)
    pixels[:, :, 0] = 10
    pixels[:, :, 1] = 20
    pixels[:, :, 2] = 30
    pixels[0, 0] = (1, 2, 3)

    msg = Image()
    msg.header.stamp.sec = 123
    msg.header.stamp.nanosec = 456789
    msg.header.frame_id = 'camera_optical_frame'
    msg.height = height
    msg.width = width
    msg.encoding = 'bgr8'
    msg.is_bigendian = False
    msg.step = width * 3
    msg.data = pixels.tobytes()
    return msg


def test_passthrough_preserves_header_and_size() -> None:
    bridge = CvBridge()
    original = _make_bgr8_image()

    result = image_passthrough(bridge, original)

    assert result.header.stamp.sec == 123
    assert result.header.stamp.nanosec == 456789
    assert result.header.frame_id == 'camera_optical_frame'
    assert result.height == original.height
    assert result.width == original.width
    assert result.encoding == 'bgr8'
    assert bytes(result.data) == bytes(original.data)
