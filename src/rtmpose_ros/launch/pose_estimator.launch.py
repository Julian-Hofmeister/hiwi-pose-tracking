"""Start one pose estimator. Same YAML as every other instance.

Topics stay relative. Change input/output via ``namespace`` and remapping arguments.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory('rtmpose_ros')
    default_config = os.path.join(pkg_share, 'config', 'rtmpose.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('config', default_value=default_config),
        DeclareLaunchArgument('backend', default_value='rtmpose'),
        DeclareLaunchArgument('namespace', default_value=''),
        DeclareLaunchArgument('image_topic', default_value='image'),
        DeclareLaunchArgument('debug_image_topic', default_value='debug_image'),
        DeclareLaunchArgument('poses_topic', default_value='poses'),
        Node(
            package='rtmpose_ros',
            executable='pose_estimator',
            name='pose_estimator',
            namespace=LaunchConfiguration('namespace'),
            parameters=[
                LaunchConfiguration('config'),
                {'backend': LaunchConfiguration('backend')},
            ],
            remappings=[
                ('image', LaunchConfiguration('image_topic')),
                ('debug_image', LaunchConfiguration('debug_image_topic')),
                ('poses', LaunchConfiguration('poses_topic')),
            ],
            output='screen',
        ),
    ])
