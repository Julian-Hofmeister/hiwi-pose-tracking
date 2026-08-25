import importlib.util
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription


def _load_launch(filename: str):
    path = os.path.join(get_package_share_directory('rtmpose_ros'), 'launch', filename)
    spec = importlib.util.spec_from_file_location('rtmpose_launch', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pose_estimator_launch_loads() -> None:
    description = _load_launch('pose_estimator.launch.py').generate_launch_description()
    assert isinstance(description, LaunchDescription)
    assert len(description.entities) > 0


def test_mock_camera_launch_loads() -> None:
    description = _load_launch('mock_camera.launch.py').generate_launch_description()
    assert isinstance(description, LaunchDescription)
    assert len(description.entities) > 0


def test_multi_camera_launch_loads() -> None:
    description = _load_launch('multi_camera.launch.py').generate_launch_description()
    assert isinstance(description, LaunchDescription)
    assert len(description.entities) > 0
