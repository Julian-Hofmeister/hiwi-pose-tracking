import numpy as np

from rtmpose_ros.inference import (
    PoseEstimatorConfig,
    _bbox_from_prediction,
    _person_from_prediction,
    create_estimator,
)
from rtmpose_ros.models import COCO_17_KEYPOINT_NAMES


def test_mock_estimator_returns_coco_person() -> None:
    image = np.zeros((120, 160, 3), dtype=np.uint8)
    estimator = create_estimator(PoseEstimatorConfig(backend='mock'))
    result = estimator.estimate(image)

    assert result.image_width == 160
    assert result.image_height == 120
    assert result.model_name == 'mock'
    assert result.skeleton_type == 'coco_17'
    assert len(result.poses) == 1
    person = result.poses[0]
    assert person.person_id == 0
    assert person.bounding_box is not None
    assert person.bounding_box.width > 0
    assert len(person.keypoints) == len(COCO_17_KEYPOINT_NAMES)
    assert {kp.name for kp in person.keypoints} == set(COCO_17_KEYPOINT_NAMES)
    assert all(0.0 <= kp.score <= 1.0 for kp in person.keypoints)
    assert result.keypoint_names == COCO_17_KEYPOINT_NAMES


def test_unknown_backend_is_rejected() -> None:
    try:
        create_estimator(PoseEstimatorConfig(backend='yolo'))
    except ValueError as exc:
        assert 'yolo' in str(exc)
    else:
        raise AssertionError('expected ValueError')


def test_prediction_converter_maps_keypoints_scores_and_bbox() -> None:
    config = PoseEstimatorConfig(keypoint_threshold=0.4)
    prediction = {
        'keypoints': [[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]],
        'keypoint_scores': [0.9, 0.2, 0.8],
        'bbox': [5.0, 6.0, 25.0, 46.0],
        'bbox_score': 0.7,
    }
    person = _person_from_prediction(3, prediction, config)
    assert person.person_id == 3
    assert person.bounding_box == _bbox_from_prediction(prediction)
    assert person.bounding_box is not None
    assert person.bounding_box.x == 5.0
    assert person.bounding_box.width == 20.0
    assert person.bounding_box.height == 40.0
    assert [kp.id for kp in person.keypoints] == [0, 2]
    assert person.keypoints[0].name == 'nose'
    assert person.keypoints[0].score == 0.9
