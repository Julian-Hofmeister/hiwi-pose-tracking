import time

import numpy as np
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from rtmpose_ros.inference import MockPoseEstimator, PoseEstimator, PoseEstimatorConfig
from rtmpose_ros.models import COCO_17_KEYPOINT_NAMES, PoseEstimationResult
from rtmpose_ros.node import PoseEstimatorNode
from human_pose_msgs.msg import PersonPose2DArray


def _make_bgr8_image(width: int = 16, height: int = 12, fill: int = 40) -> Image:
    pixels = np.full((height, width, 3), fill, dtype=np.uint8)
    msg = Image()
    msg.header.stamp.sec = 42
    msg.header.stamp.nanosec = 24
    msg.header.frame_id = 'test_camera'
    msg.height = height
    msg.width = width
    msg.encoding = 'bgr8'
    msg.is_bigendian = False
    msg.step = width * 3
    msg.data = pixels.tobytes()
    return msg


def _mock_estimator() -> MockPoseEstimator:
    return MockPoseEstimator(PoseEstimatorConfig(backend='mock'))


def _make_node(**kwargs) -> PoseEstimatorNode:
    if 'estimator' not in kwargs:
        kwargs['estimator'] = _mock_estimator()
    return PoseEstimatorNode(**kwargs)


def _spin_until(executor: SingleThreadedExecutor, predicate, timeout_sec: float) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        executor.spin_once(timeout_sec=0.05)
        if predicate():
            return True
    return False


def _run_image_roundtrip(estimator: PoseEstimatorNode, outgoing: Image) -> Image:
    received: list[Image] = []
    helper = rclpy.create_node('test_helper_' + str(time.monotonic_ns()))
    publisher = helper.create_publisher(Image, 'image', qos_profile_sensor_data)
    helper.create_subscription(
        Image,
        'debug_image',
        received.append,
        qos_profile_sensor_data,
    )
    executor = SingleThreadedExecutor()
    executor.add_node(estimator)
    executor.add_node(helper)
    try:
        connected = _spin_until(
            executor,
            lambda: publisher.get_subscription_count() >= 1,
            timeout_sec=5.0,
        )
        assert connected, 'pose_estimator did not subscribe to relative topic "image"'
        got_message = _spin_until(
            executor,
            lambda: (publisher.publish(outgoing) or True) and len(received) > 0,
            timeout_sec=5.0,
        )
        assert got_message, 'no debug_image received'
        return received[0]
    finally:
        helper.destroy_node()
        executor.shutdown()


def test_node_republishes_image_and_header(ros_context) -> None:
    estimator = _make_node()
    try:
        result = _run_image_roundtrip(estimator, _make_bgr8_image())
    finally:
        estimator.destroy_node()

    assert result.header.stamp.sec == 42
    assert result.header.stamp.nanosec == 24
    assert result.header.frame_id == 'test_camera'
    assert result.width == 16
    assert result.height == 12
    assert result.encoding == 'bgr8'


def test_node_uses_namespace_for_topics(ros_context) -> None:
    received: list[Image] = []
    estimator = _make_node(namespace='camera_1')
    helper = rclpy.create_node('test_helper_ns')
    publisher = helper.create_publisher(Image, '/camera_1/image', qos_profile_sensor_data)
    helper.create_subscription(
        Image,
        '/camera_1/debug_image',
        received.append,
        qos_profile_sensor_data,
    )
    executor = SingleThreadedExecutor()
    executor.add_node(estimator)
    executor.add_node(helper)
    try:
        connected = _spin_until(
            executor,
            lambda: publisher.get_subscription_count() >= 1,
            timeout_sec=5.0,
        )
        assert connected, 'namespaced pose_estimator did not subscribe to /camera_1/image'
        outgoing = _make_bgr8_image()
        got_message = _spin_until(
            executor,
            lambda: (publisher.publish(outgoing) or True) and len(received) > 0,
            timeout_sec=5.0,
        )
        assert got_message, 'no namespaced debug_image received'
        assert received[0].header.frame_id == 'test_camera'
    finally:
        estimator.destroy_node()
        helper.destroy_node()
        executor.shutdown()


def test_node_stays_alive_on_empty_detections(ros_context) -> None:
    class EmptyEstimator(PoseEstimator):
        def __init__(self) -> None:
            super().__init__(PoseEstimatorConfig(backend='mock'))

        def estimate(self, image: np.ndarray) -> PoseEstimationResult:
            height, width = image.shape[:2]
            return PoseEstimationResult(
                image_width=int(width),
                image_height=int(height),
                skeleton_type='coco_17',
                model_name='empty',
                poses=(),
            )

    estimator = _make_node(estimator=EmptyEstimator())
    try:
        result = _run_image_roundtrip(estimator, _make_bgr8_image())
    finally:
        estimator.destroy_node()

    assert result.width == 16
    assert result.height == 12
    assert result.encoding == 'bgr8'


def test_node_ignores_invalid_image_then_recovers(ros_context) -> None:
    estimator = _make_node()
    helper = rclpy.create_node('test_helper_invalid')
    publisher = helper.create_publisher(Image, 'image', qos_profile_sensor_data)
    received: list[Image] = []
    helper.create_subscription(
        Image,
        'debug_image',
        received.append,
        qos_profile_sensor_data,
    )
    executor = SingleThreadedExecutor()
    executor.add_node(estimator)
    executor.add_node(helper)
    try:
        connected = _spin_until(
            executor,
            lambda: publisher.get_subscription_count() >= 1,
            timeout_sec=5.0,
        )
        assert connected
        bad = Image()
        bad.header.frame_id = 'broken'
        bad.height = 8
        bad.width = 8
        bad.encoding = 'bgr8'
        bad.step = 24
        bad.data = b''
        publisher.publish(bad)
        _spin_until(executor, lambda: False, timeout_sec=0.3)
        assert received == []

        good = _make_bgr8_image()
        got_message = _spin_until(
            executor,
            lambda: (publisher.publish(good) or True) and len(received) > 0,
            timeout_sec=5.0,
        )
        assert got_message
        assert received[0].header.frame_id == 'test_camera'
    finally:
        estimator.destroy_node()
        helper.destroy_node()
        executor.shutdown()


def test_node_survives_inference_error(ros_context) -> None:
    class FailOnceEstimator(PoseEstimator):
        def __init__(self) -> None:
            super().__init__(PoseEstimatorConfig(backend='mock'))
            self.calls = 0
            self._inner = MockPoseEstimator(self.config)

        def estimate(self, image: np.ndarray) -> PoseEstimationResult:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError('inference failed')
            return self._inner.estimate(image)

    failing = FailOnceEstimator()
    estimator = _make_node(estimator=failing)
    helper = rclpy.create_node('test_helper_fail')
    publisher = helper.create_publisher(Image, 'image', qos_profile_sensor_data)
    received: list[Image] = []
    helper.create_subscription(
        Image,
        'debug_image',
        received.append,
        qos_profile_sensor_data,
    )
    executor = SingleThreadedExecutor()
    executor.add_node(estimator)
    executor.add_node(helper)
    try:
        assert _spin_until(
            executor,
            lambda: publisher.get_subscription_count() >= 1,
            timeout_sec=5.0,
        )
        first = _make_bgr8_image(fill=10)
        _spin_until(
            executor,
            lambda: (publisher.publish(first) or True) and failing.calls >= 1,
            timeout_sec=5.0,
        )
        assert received == []
        second = _make_bgr8_image(fill=80)
        got_message = _spin_until(
            executor,
            lambda: (publisher.publish(second) or True) and len(received) > 0,
            timeout_sec=5.0,
        )
        assert got_message
        assert failing.calls >= 2
    finally:
        estimator.destroy_node()
        helper.destroy_node()
        executor.shutdown()


def test_node_builds_in_process_mock_from_parameter(ros_context) -> None:
    estimator = PoseEstimatorNode(
        parameter_overrides=[Parameter('backend', Parameter.Type.STRING, 'mock')]
    )
    try:
        result = _run_image_roundtrip(estimator, _make_bgr8_image())
        assert result.encoding == 'bgr8'
        assert estimator._estimator is not None
        assert estimator._estimator.config.backend == 'mock'
    finally:
        estimator.destroy_node()


def test_missing_rtmpose_python_does_not_crash_the_node(ros_context) -> None:
    node = PoseEstimatorNode(
        parameter_overrides=[
            Parameter('backend', Parameter.Type.STRING, 'rtmpose'),
            Parameter('rtmpose_python', Parameter.Type.STRING, '/definitely/missing/python'),
        ]
    )
    try:
        assert node.get_name() == 'pose_estimator'
        assert node._estimator is None
    finally:
        node.destroy_node()


def test_node_publishes_poses_with_image_header(ros_context) -> None:
    estimator = _make_node()
    helper = rclpy.create_node('test_helper_poses')
    publisher = helper.create_publisher(Image, 'image', qos_profile_sensor_data)
    received: list[PersonPose2DArray] = []
    helper.create_subscription(
        PersonPose2DArray,
        'poses',
        received.append,
        qos_profile_sensor_data,
    )
    executor = SingleThreadedExecutor()
    executor.add_node(estimator)
    executor.add_node(helper)
    try:
        assert _spin_until(
            executor,
            lambda: publisher.get_subscription_count() >= 1,
            timeout_sec=5.0,
        )
        outgoing = _make_bgr8_image()
        got = _spin_until(
            executor,
            lambda: (publisher.publish(outgoing) or True) and len(received) > 0,
            timeout_sec=5.0,
        )
        assert got, 'no poses message received'
        msg = received[0]
        assert msg.header.stamp.sec == 42
        assert msg.header.stamp.nanosec == 24
        assert msg.header.frame_id == 'test_camera'
        assert msg.image_width == 16
        assert msg.image_height == 12
        assert msg.skeleton_type == 'coco_17'
        assert list(msg.keypoint_names) == list(COCO_17_KEYPOINT_NAMES)
        assert len(msg.poses) == 1
        assert len(msg.poses[0].keypoints) == 17
        assert msg.poses[0].has_bounding_box
    finally:
        estimator.destroy_node()
        helper.destroy_node()
        executor.shutdown()


def test_node_publishes_empty_pose_array(ros_context) -> None:
    class EmptyEstimator(PoseEstimator):
        def __init__(self) -> None:
            super().__init__(PoseEstimatorConfig(backend='mock'))

        def estimate(self, image: np.ndarray) -> PoseEstimationResult:
            height, width = image.shape[:2]
            return PoseEstimationResult(
                image_width=int(width),
                image_height=int(height),
                skeleton_type='coco_17',
                model_name='empty',
                poses=(),
            )

    estimator = _make_node(estimator=EmptyEstimator())
    helper = rclpy.create_node('test_helper_empty_poses')
    publisher = helper.create_publisher(Image, 'image', qos_profile_sensor_data)
    received: list[PersonPose2DArray] = []
    helper.create_subscription(
        PersonPose2DArray,
        'poses',
        received.append,
        qos_profile_sensor_data,
    )
    executor = SingleThreadedExecutor()
    executor.add_node(estimator)
    executor.add_node(helper)
    try:
        assert _spin_until(
            executor,
            lambda: publisher.get_subscription_count() >= 1,
            timeout_sec=5.0,
        )
        outgoing = _make_bgr8_image()
        got = _spin_until(
            executor,
            lambda: (publisher.publish(outgoing) or True) and len(received) > 0,
            timeout_sec=5.0,
        )
        assert got, 'empty pose array was not published'
        assert list(received[0].poses) == []
        assert received[0].header.frame_id == 'test_camera'
    finally:
        estimator.destroy_node()
        helper.destroy_node()
        executor.shutdown()


def test_node_publishes_three_people_with_confidence(ros_context) -> None:
    class ThreePeople(PoseEstimator):
        def __init__(self) -> None:
            super().__init__(PoseEstimatorConfig(backend='mock'))

        def estimate(self, image: np.ndarray) -> PoseEstimationResult:
            from rtmpose_ros.models import Keypoint2D, PersonPose2D

            height, width = image.shape[:2]
            people = []
            for index, score in enumerate((0.9, 0.6, 0.3)):
                people.append(
                    PersonPose2D(
                        person_id=index,
                        score=score,
                        keypoints=(
                            Keypoint2D(id=0, x=float(index), y=1.0, score=score, name='nose'),
                        ),
                    )
                )
            return PoseEstimationResult(
                image_width=int(width),
                image_height=int(height),
                skeleton_type='coco_17',
                model_name='three',
                poses=tuple(people),
            )

    estimator = _make_node(estimator=ThreePeople())
    helper = rclpy.create_node('test_helper_three')
    publisher = helper.create_publisher(Image, 'image', qos_profile_sensor_data)
    received: list[PersonPose2DArray] = []
    helper.create_subscription(
        PersonPose2DArray, 'poses', received.append, qos_profile_sensor_data
    )
    executor = SingleThreadedExecutor()
    executor.add_node(estimator)
    executor.add_node(helper)
    try:
        assert _spin_until(
            executor, lambda: publisher.get_subscription_count() >= 1, timeout_sec=5.0
        )
        outgoing = _make_bgr8_image()
        got = _spin_until(
            executor,
            lambda: (publisher.publish(outgoing) or True) and len(received) > 0,
            timeout_sec=5.0,
        )
        assert got
        people = received[0].poses
        assert len(people) == 3
        assert [round(p.score, 1) for p in people] == [0.9, 0.6, 0.3]
        assert received[0].header.frame_id == 'test_camera'
        stats = estimator.snapshot_stats()
        assert stats['frames_received'] >= 1
        assert stats['poses_published'] >= 1
    finally:
        estimator.destroy_node()
        helper.destroy_node()
        executor.shutdown()


def test_destroy_node_stops_worker_thread(ros_context) -> None:
    estimator = _make_node()
    worker = estimator._worker
    assert worker is not None
    assert worker.is_alive()
    estimator.destroy_node()
    assert estimator._worker is None
    assert not worker.is_alive()

