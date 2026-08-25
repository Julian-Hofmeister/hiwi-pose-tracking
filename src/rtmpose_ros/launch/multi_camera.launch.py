"""Start one pose-estimator pipeline per camera. Shared YAML, separate namespaces."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from rtmpose_ros.camera_inventory import load_camera_inventory


def _include_cameras(context, *args, **kwargs):
    pkg_share = get_package_share_directory('rtmpose_ros')
    mock_camera = os.path.join(pkg_share, 'launch', 'mock_camera.launch.py')
    cameras = load_camera_inventory(LaunchConfiguration('cameras_config').perform(context))
    estimator_config = LaunchConfiguration('estimator_config').perform(context)
    source_config = LaunchConfiguration('source_config').perform(context)
    backend = LaunchConfiguration('backend').perform(context)
    source_type = LaunchConfiguration('source_type').perform(context)
    path = LaunchConfiguration('path').perform(context)
    fps = LaunchConfiguration('fps').perform(context)

    actions = []
    for camera in cameras:
        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(mock_camera),
                launch_arguments={
                    'namespace': camera['namespace'],
                    'frame_id': camera['frame_id'],
                    'estimator_config': estimator_config,
                    'source_config': source_config,
                    'backend': backend,
                    'source_type': source_type,
                    'path': path,
                    'fps': fps,
                    'image_topic': camera['image_topic'],
                    'debug_image_topic': camera['debug_image_topic'],
                    'poses_topic': camera['poses_topic'],
                }.items(),
            )
        )
    return actions


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory('rtmpose_ros')
    default_estimator_config = os.path.join(pkg_share, 'config', 'rtmpose.yaml')
    default_source_config = os.path.join(pkg_share, 'config', 'image_source.yaml')
    default_cameras_config = os.path.join(pkg_share, 'config', 'cameras.yaml')
    default_test_image = os.path.join(pkg_share, 'test_data', 'test_pattern.ppm')

    return LaunchDescription([
        DeclareLaunchArgument('cameras_config', default_value=default_cameras_config),
        DeclareLaunchArgument('estimator_config', default_value=default_estimator_config),
        DeclareLaunchArgument('source_config', default_value=default_source_config),
        DeclareLaunchArgument('backend', default_value='rtmpose'),
        DeclareLaunchArgument('source_type', default_value='synthetic'),
        DeclareLaunchArgument('path', default_value=default_test_image),
        DeclareLaunchArgument('fps', default_value='15.0'),
        OpaqueFunction(function=_include_cameras),
    ])
