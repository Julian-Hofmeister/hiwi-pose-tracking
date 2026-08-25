"""RGB image conversion helpers for the pose estimator node."""

from cv_bridge import CvBridge
from sensor_msgs.msg import Image


def copy_header(source: Image, target: Image) -> None:
    """Copy stamp and frame_id from the camera image onto the outgoing message."""
    target.header.stamp.sec = source.header.stamp.sec
    target.header.stamp.nanosec = source.header.stamp.nanosec
    target.header.frame_id = source.header.frame_id


def image_passthrough(bridge: CvBridge, msg: Image) -> Image:
    """Convert a ROS image to OpenCV and back, preserving the original header."""
    cv_image = bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
    out = bridge.cv2_to_imgmsg(cv_image, encoding=msg.encoding)
    copy_header(msg, out)
    return out
