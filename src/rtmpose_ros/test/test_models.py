from rtmpose_ros.inference import MockPoseEstimator, PoseEstimatorConfig
from rtmpose_ros.models import result_from_dict, result_to_dict
import numpy as np


def test_result_dict_roundtrip() -> None:
    image = np.zeros((40, 50, 3), dtype=np.uint8)
    original = MockPoseEstimator(PoseEstimatorConfig(backend='mock')).estimate(image)
    restored = result_from_dict(result_to_dict(original))

    assert restored == original


def test_result_from_dict_empty_poses() -> None:
    restored = result_from_dict(
        {
            'image_width': 8,
            'image_height': 6,
            'skeleton_type': 'coco_17',
            'model_name': 'none',
            'poses': [],
        }
    )
    assert restored.poses == ()
    assert restored.image_width == 8
    assert restored.image_height == 6
