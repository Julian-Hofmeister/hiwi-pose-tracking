from setuptools import find_packages, setup

package_name = 'rtmpose_ros'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', [
            'config/rtmpose.yaml',
            'config/image_source.yaml',
            'config/cameras.yaml',
        ]),
        ('share/' + package_name + '/launch', [
            'launch/pose_estimator.launch.py',
            'launch/mock_camera.launch.py',
            'launch/multi_camera.launch.py',
        ]),
        ('share/' + package_name + '/test_data', [
            'test_data/test_pattern.ppm',
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Julian Hofmeister',
    maintainer_email='Julian-Hofmeister@users.noreply.github.com',
    description='ROS2 Jazzy node for RTMPose 2D pose estimation.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'pose_estimator = rtmpose_ros.node:main',
            'image_source = rtmpose_ros.image_source:main',
            'preview_writer = rtmpose_ros.preview_writer:main',
        ],
    },
)
