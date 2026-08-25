"""Internal pose-estimation data models. These are independent of ROS messages."""

from __future__ import annotations

from dataclasses import dataclass, field

# COCO body keypoints used by the default RTMPose human models.
COCO_17_KEYPOINT_NAMES: tuple[str, ...] = (
    'nose',
    'left_eye',
    'right_eye',
    'left_ear',
    'right_ear',
    'left_shoulder',
    'right_shoulder',
    'left_elbow',
    'right_elbow',
    'left_wrist',
    'right_wrist',
    'left_hip',
    'right_hip',
    'left_knee',
    'right_knee',
    'left_ankle',
    'right_ankle',
)


@dataclass(frozen=True)
class Keypoint2D:
    id: int
    x: float
    y: float
    score: float
    name: str = ''


@dataclass(frozen=True)
class BoundingBox2D:
    """Axis-aligned box in pixel coordinates, origin at the top-left of the image."""

    x: float
    y: float
    width: float
    height: float
    score: float = 0.0


@dataclass(frozen=True)
class PersonPose2D:
    """One detected person. ``person_id`` is only unique within a single frame."""

    person_id: int
    score: float
    keypoints: tuple[Keypoint2D, ...]
    bounding_box: BoundingBox2D | None = None


@dataclass(frozen=True)
class PoseEstimationResult:
    image_width: int
    image_height: int
    skeleton_type: str
    model_name: str
    poses: tuple[PersonPose2D, ...] = field(default_factory=tuple)
    # Schema for this source: index is Keypoint2D.id. Length is the skeleton
    # size (e.g. 17), not the number of detected joints after thresholding.
    keypoint_names: tuple[str, ...] = field(default_factory=tuple)


def result_to_dict(result: PoseEstimationResult) -> dict:
    return {
        'image_width': result.image_width,
        'image_height': result.image_height,
        'skeleton_type': result.skeleton_type,
        'model_name': result.model_name,
        'keypoint_names': list(result.keypoint_names),
        'poses': [
            {
                'person_id': person.person_id,
                'score': person.score,
                'bounding_box': None
                if person.bounding_box is None
                else {
                    'x': person.bounding_box.x,
                    'y': person.bounding_box.y,
                    'width': person.bounding_box.width,
                    'height': person.bounding_box.height,
                    'score': person.bounding_box.score,
                },
                'keypoints': [
                    {
                        'id': keypoint.id,
                        'name': keypoint.name,
                        'x': keypoint.x,
                        'y': keypoint.y,
                        'score': keypoint.score,
                    }
                    for keypoint in person.keypoints
                ],
            }
            for person in result.poses
        ],
    }


def result_from_dict(payload: dict) -> PoseEstimationResult:
    poses = []
    for person in payload.get('poses') or []:
        bbox_raw = person.get('bounding_box')
        bbox = None
        if bbox_raw is not None:
            bbox = BoundingBox2D(
                x=float(bbox_raw['x']),
                y=float(bbox_raw['y']),
                width=float(bbox_raw['width']),
                height=float(bbox_raw['height']),
                score=float(bbox_raw.get('score', 0.0)),
            )
        keypoints = tuple(
            Keypoint2D(
                id=int(point['id']),
                x=float(point['x']),
                y=float(point['y']),
                score=float(point['score']),
                name=str(point.get('name', '')),
            )
            for point in person.get('keypoints') or []
        )
        poses.append(
            PersonPose2D(
                person_id=int(person.get('person_id', 0)),
                score=float(person.get('score', 0.0)),
                keypoints=keypoints,
                bounding_box=bbox,
            )
        )
    return PoseEstimationResult(
        image_width=int(payload['image_width']),
        image_height=int(payload['image_height']),
        skeleton_type=str(payload.get('skeleton_type', 'coco_17')),
        model_name=str(payload.get('model_name', '')),
        poses=tuple(poses),
        keypoint_names=tuple(str(name) for name in payload.get('keypoint_names') or ()),
    )
