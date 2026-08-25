"""Draw 2D poses onto a BGR image. No ROS and no MMPose imports."""

from __future__ import annotations

import cv2
import numpy as np

from rtmpose_ros.models import PoseEstimationResult

# COCO-17 skeleton edges by keypoint id.
COCO_17_SKELETON: tuple[tuple[int, int], ...] = (
    (0, 1), (0, 2), (1, 3), (2, 4),
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
)

_BBOX_COLOR = (40, 220, 40)
_BONE_COLOR = (0, 200, 255)
_POINT_COLOR = (0, 80, 255)


def draw_poses(image: np.ndarray, result: PoseEstimationResult) -> np.ndarray:
    """Return a copy of ``image`` with bounding boxes and skeletons drawn."""
    canvas = image.copy()
    for person in result.poses:
        if person.bounding_box is not None:
            x1 = int(round(person.bounding_box.x))
            y1 = int(round(person.bounding_box.y))
            x2 = int(round(person.bounding_box.x + person.bounding_box.width))
            y2 = int(round(person.bounding_box.y + person.bounding_box.height))
            cv2.rectangle(canvas, (x1, y1), (x2, y2), _BBOX_COLOR, 2)
            cv2.putText(
                canvas,
                f'id={person.person_id} {person.score:.2f}',
                (x1, max(y1 - 6, 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                _BBOX_COLOR,
                1,
                cv2.LINE_AA,
            )
        by_id = {keypoint.id: keypoint for keypoint in person.keypoints}
        for start_id, end_id in COCO_17_SKELETON:
            start = by_id.get(start_id)
            end = by_id.get(end_id)
            if start is None or end is None:
                continue
            cv2.line(
                canvas,
                (int(round(start.x)), int(round(start.y))),
                (int(round(end.x)), int(round(end.y))),
                _BONE_COLOR,
                2,
                cv2.LINE_AA,
            )
        for keypoint in person.keypoints:
            cv2.circle(
                canvas,
                (int(round(keypoint.x)), int(round(keypoint.y))),
                3,
                _POINT_COLOR,
                -1,
                cv2.LINE_AA,
            )
    return canvas
