import numpy as np

from rtmpose_ros.inference import MockPoseEstimator, PoseEstimatorConfig
from rtmpose_ros.models import PoseEstimationResult
from rtmpose_ros.visualization import draw_poses


def test_draw_poses_keeps_size_and_changes_pixels() -> None:
    image = np.zeros((80, 100, 3), dtype=np.uint8)
    result = MockPoseEstimator(PoseEstimatorConfig(backend='mock')).estimate(image)
    overlay = draw_poses(image, result)

    assert overlay.shape == image.shape
    assert overlay.dtype == image.dtype
    assert not np.array_equal(overlay, image)
    assert np.array_equal(image, np.zeros((80, 100, 3), dtype=np.uint8))


def test_draw_poses_empty_result_is_a_copy() -> None:
    image = np.full((16, 20, 3), 90, dtype=np.uint8)
    result = PoseEstimationResult(
        image_width=20,
        image_height=16,
        skeleton_type='coco_17',
        model_name='empty',
        poses=(),
    )
    overlay = draw_poses(image, result)

    assert overlay.shape == image.shape
    assert np.array_equal(overlay, image)
    assert overlay is not image
