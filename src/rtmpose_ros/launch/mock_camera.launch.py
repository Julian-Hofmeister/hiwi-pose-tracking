"""Start one mock camera and one pose estimator.

Topics stay relative. Change input/output via ``namespace`` and remapping arguments.
Model parameters come from the shared YAML (``estimator_config``).
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory('rtmpose_ros')
    default_estimator_config = os.path.join(pkg_share, 'config', 'rtmpose.yaml')
    default_source_config = os.path.join(pkg_share, 'config', 'image_source.yaml')
    default_test_image = os.path.join(pkg_share, 'test_data', 'test_pattern.ppm')

    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value=''),
        DeclareLaunchArgument('estimator_config', default_value=default_estimator_config),
        DeclareLaunchArgument('source_config', default_value=default_source_config),
        DeclareLaunchArgument('backend', default_value='rtmpose'),
        DeclareLaunchArgument(
            'pose_model', default_value='rtmpose-t_8xb256-420e_body8-256x192'
        ),
        DeclareLaunchArgument('detector_model', default_value='rtmdet-t'),
        DeclareLaunchArgument('source_type', default_value='synthetic'),
        DeclareLaunchArgument('path', default_value=default_test_image),
        DeclareLaunchArgument('device_index', default_value='0'),
        DeclareLaunchArgument('fps', default_value='15.0'),
        DeclareLaunchArgument('frame_id', default_value='camera_optical_frame'),
        DeclareLaunchArgument('image_topic', default_value='image'),
        DeclareLaunchArgument('debug_image_topic', default_value='debug_image'),
        DeclareLaunchArgument('poses_topic', default_value='poses'),
        DeclareLaunchArgument('preview_path', default_value='/ws/tmp/live_preview.jpg'),
        Node(
            package='rtmpose_ros',
            executable='image_source',
            name='image_source',
            namespace=LaunchConfiguration('namespace'),
            parameters=[
                LaunchConfiguration('source_config'),
                {
                    'source_type': LaunchConfiguration('source_type'),
                    'path': LaunchConfiguration('path'),
                    'device_index': ParameterValue(
                        LaunchConfiguration('device_index'), value_type=int
                    ),
                    'fps': ParameterValue(LaunchConfiguration('fps'), value_type=float),
                    'frame_id': LaunchConfiguration('frame_id'),
                },
            ],
            remappings=[
                ('image', LaunchConfiguration('image_topic')),
            ],
            output='screen',
        ),
        Node(
            package='rtmpose_ros',
            executable='pose_estimator',
            name='pose_estimator',
            namespace=LaunchConfiguration('namespace'),
            parameters=[
                LaunchConfiguration('estimator_config'),
                {
                    'backend': LaunchConfiguration('backend'),
                    'pose_model': LaunchConfiguration('pose_model'),
                    'detector_model': LaunchConfiguration('detector_model'),
                },
            ],
            remappings=[
                ('image', LaunchConfiguration('image_topic')),
                ('debug_image', LaunchConfiguration('debug_image_topic')),
                ('poses', LaunchConfiguration('poses_topic')),
            ],
            output='screen',
        ),
        Node(
            package='rtmpose_ros',
            executable='preview_writer',
            name='preview_writer',
            namespace=LaunchConfiguration('namespace'),
            parameters=[{'output_path': LaunchConfiguration('preview_path')}],
            remappings=[
                ('debug_image', LaunchConfiguration('debug_image_topic')),
            ],
            output='screen',
        ),
    ])
