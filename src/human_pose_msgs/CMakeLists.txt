cmake_minimum_required(VERSION 3.8)
project(human_pose_msgs)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Keypoint2D.msg"
  "msg/BoundingBox2D.msg"
  "msg/PersonPose2D.msg"
  "msg/PersonPose2DArray.msg"
  DEPENDENCIES std_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
