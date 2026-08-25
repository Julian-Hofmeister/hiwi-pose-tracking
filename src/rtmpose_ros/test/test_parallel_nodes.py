import time

import numpy as np
import rclpy
from human_pose_msgs.msg import PersonPose2DArray
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from rtmpose_ros.inference import MockPoseEstimator, PoseEstimatorConfig
from rtmpose_ros.node import PoseEstimatorNode


def _image(frame_id: str, fill: int) -> Image:
    width, height = 16, 12
    pixels = np.full((height, width, 3), fill, dtype=np.uint8)
    msg = Image()
    msg.header.stamp.sec = fill
    msg.header.frame_id = frame_id
    msg.height = height
    msg.width = width
    msg.encoding = 'bgr8'
    msg.is_bigendian = False
    msg.step = width * 3
    msg.data = pixels.tobytes()
    return msg


def _spin_until(executor: SingleThreadedExecutor, predicate, timeout_sec: float) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        executor.spin_once(timeout_sec=0.05)
        if predicate():
            return True
    return False


def test_two_namespaced_nodes_do_not_mix_results(ros_context) -> None:
    config = PoseEstimatorConfig(backend='mock')
    node_a = PoseEstimatorNode(namespace='camera_1', estimator=MockPoseEstimator(config))
    node_b = PoseEstimatorNode(namespace='camera_2', estimator=MockPoseEstimator(config))
    helper = rclpy.create_node('parallel_helper')

    pub_a = helper.create_publisher(Image, '/camera_1/image', qos_profile_sensor_data)
    pub_b = helper.create_publisher(Image, '/camera_2/image', qos_profile_sensor_data)
    poses_a: list[PersonPose2DArray] = []
    poses_b: list[PersonPose2DArray] = []
    helper.create_subscription(
        PersonPose2DArray, '/camera_1/poses', poses_a.append, qos_profile_sensor_data
    )
    helper.create_subscription(
        PersonPose2DArray, '/camera_2/poses', poses_b.append, qos_profile_sensor_data
    )

    executor = SingleThreadedExecutor()
    executor.add_node(node_a)
    executor.add_node(node_b)
    executor.add_node(helper)
    try:
        assert _spin_until(
            executor,
            lambda: pub_a.get_subscription_count() >= 1 and pub_b.get_subscription_count() >= 1,
            timeout_sec=5.0,
        )

        only_a = _image('camera_1_optical_frame', fill=11)
        got_a = _spin_until(
            executor,
            lambda: (pub_a.publish(only_a) or True) and len(poses_a) > 0,
            timeout_sec=5.0,
        )
        assert got_a, 'camera_1 produced no poses'
        assert poses_b == [], 'camera_2 received a pose although only camera_1 was published'
        assert poses_a[0].header.frame_id == 'camera_1_optical_frame'
        assert poses_a[0].header.stamp.sec == 11

        only_b = _image('camera_2_optical_frame', fill=22)
        got_b = _spin_until(
            executor,
            lambda: (pub_b.publish(only_b) or True) and len(poses_b) > 0,
            timeout_sec=5.0,
        )
        assert got_b, 'camera_2 produced no poses'
        assert all(msg.header.frame_id == 'camera_1_optical_frame' for msg in poses_a)
        assert poses_b[0].header.frame_id == 'camera_2_optical_frame'
        assert poses_b[0].header.stamp.sec == 22
    finally:
        node_a.destroy_node()
        node_b.destroy_node()
        helper.destroy_node()
        executor.shutdown()
