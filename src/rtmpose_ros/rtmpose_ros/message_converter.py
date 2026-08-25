"""Convert internal pose results to ``human_pose_msgs``.

This module may import ROS messages. It must not import MMPose or create
publishers/subscribers.
"""

from __future__ import annotations

from human_pose_msgs.msg import BoundingBox2D as BoundingBox2DMsg
from human_pose_msgs.msg import Keypoint2D as Keypoint2DMsg
from human_pose_msgs.msg import PersonPose2D as PersonPose2DMsg
from human_pose_msgs.msg import PersonPose2DArray
from std_msgs.msg import Header

from rtmpose_ros.models import (
    COCO_17_KEYPOINT_NAMES,
    BoundingBox2D,
    PoseEstimationResult,
)


def result_to_pose_array(result: PoseEstimationResult, header: Header) -> PersonPose2DArray:
    """Map one estimator result onto a ROS pose array. ``header`` is copied."""
    msg = PersonPose2DArray()
    msg.header.stamp.sec = header.stamp.sec
    msg.header.stamp.nanosec = header.stamp.nanosec
    msg.header.frame_id = header.frame_id
    msg.image_width = int(result.image_width)
    msg.image_height = int(result.image_height)
    msg.skeleton_type = result.skeleton_type
    msg.model_name = result.model_name
    msg.keypoint_names = _schema_names(result)
    msg.poses = [_person_to_msg(person) for person in result.poses]
    return msg


def _schema_names(result: PoseEstimationResult) -> list[str]:
    if result.keypoint_names:
        return list(result.keypoint_names)
    if result.skeleton_type == 'coco_17':
        return list(COCO_17_KEYPOINT_NAMES)
    names_by_id: dict[int, str] = {}
    for person in result.poses:
        for keypoint in person.keypoints:
            names_by_id.setdefault(int(keypoint.id), keypoint.name)
    if not names_by_id:
        return []
    size = max(names_by_id) + 1
    return [names_by_id.get(index, '') for index in range(size)]


def _person_to_msg(person) -> PersonPose2DMsg:
    msg = PersonPose2DMsg()
    msg.person_id = int(person.person_id)
    msg.score = float(person.score)
    if person.bounding_box is None:
        msg.has_bounding_box = False
        msg.bounding_box = BoundingBox2DMsg()
    else:
        msg.has_bounding_box = True
        msg.bounding_box = _bbox_to_msg(person.bounding_box)
    msg.keypoints = [
        Keypoint2DMsg(
            id=int(keypoint.id),
            name=keypoint.name,
            x=float(keypoint.x),
            y=float(keypoint.y),
            score=float(keypoint.score),
        )
        for keypoint in person.keypoints
    ]
    return msg


def _bbox_to_msg(box: BoundingBox2D) -> BoundingBox2DMsg:
    msg = BoundingBox2DMsg()
    msg.x = float(box.x)
    msg.y = float(box.y)
    msg.width = float(box.width)
    msg.height = float(box.height)
    msg.score = float(box.score)
    return msg
