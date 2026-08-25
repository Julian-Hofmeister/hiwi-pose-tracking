import sys

import numpy as np
import pytest

from rtmpose_ros.estimator_bridge import SubprocessPoseEstimator
from rtmpose_ros.inference import PoseEstimatorConfig


def test_subprocess_mock_estimator_roundtrip() -> None:
    estimator = SubprocessPoseEstimator(
        PoseEstimatorConfig(backend='mock'),
        python_executable=sys.executable,
    )
    try:
        image = np.full((24, 32, 3), 17, dtype=np.uint8)
        result = estimator.estimate(image)
        assert result.model_name == 'mock'
        assert result.image_width == 32
        assert result.image_height == 24
        assert len(result.poses) == 1
        assert len(result.poses[0].keypoints) == 17
    finally:
        estimator.close()


def test_subprocess_missing_python_is_a_clear_error() -> None:
    with pytest.raises(RuntimeError, match='RTMPose Python not found'):
        SubprocessPoseEstimator(
            PoseEstimatorConfig(backend='rtmpose'),
            python_executable='/definitely/missing/python',
        )


def test_subprocess_rtmpose_on_system_python_fails_clearly() -> None:
    with pytest.raises(RuntimeError, match='MMPose import failed'):
        SubprocessPoseEstimator(
            PoseEstimatorConfig(backend='rtmpose', device='cpu'),
            python_executable=sys.executable,
        )


def test_subprocess_close_stops_the_worker() -> None:
    estimator = SubprocessPoseEstimator(
        PoseEstimatorConfig(backend='mock'),
        python_executable=sys.executable,
    )
    assert estimator._proc.poll() is None
    estimator.close()
    assert estimator._proc.poll() is not None
