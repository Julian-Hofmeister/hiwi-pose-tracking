import pytest
import rclpy


@pytest.fixture(scope='session')
def ros_context():
    if not rclpy.ok():
        rclpy.init()
    yield
    if rclpy.ok():
        rclpy.shutdown()
