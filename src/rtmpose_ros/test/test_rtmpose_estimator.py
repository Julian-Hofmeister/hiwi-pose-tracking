import os
import sys
import types

import numpy as np
import pytest

from rtmpose_ros.inference import PoseEstimatorConfig, RTMPoseEstimator


def _install_fake_mmpose(monkeypatch, captured: dict, predictions: list) -> None:
    class FakeInferencer:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def __call__(self, image, **kwargs):
            captured['call_kwargs'] = kwargs
            yield {'predictions': [predictions]}

    fake_torch = types.ModuleType('torch')
    fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False)
    apis = types.ModuleType('mmpose.apis')
    apis.MMPoseInferencer = FakeInferencer
    mmpose = types.ModuleType('mmpose')
    monkeypatch.setitem(sys.modules, 'torch', fake_torch)
    monkeypatch.setitem(sys.modules, 'mmpose', mmpose)
    monkeypatch.setitem(sys.modules, 'mmpose.apis', apis)


def test_rtmpose_model_alias_is_swapped_without_ros(monkeypatch) -> None:
    captured: dict = {}
    _install_fake_mmpose(
        monkeypatch,
        captured,
        [
            {
                'keypoints': [[12.0, 24.0], [36.0, 48.0]],
                'keypoint_scores': [0.95, 0.91],
                'bbox': [4.0, 5.0, 40.0, 50.0],
                'bbox_score': 0.8,
            }
        ],
    )

    estimator = RTMPoseEstimator(
        PoseEstimatorConfig(
            pose_model='rtmpose-t',
            pose_weights='/tmp/custom.pth',
            detector_model='human',
            device='cpu',
        )
    )
    result = estimator.estimate(np.zeros((80, 100, 3), dtype=np.uint8))

    assert captured['pose2d'] == 'rtmpose-t'
    assert captured['pose2d_weights'] == '/tmp/custom.pth'
    assert captured['det_model'] == 'human'
    assert result.model_name == 'rtmpose-t'
    assert result.image_width == 100
    assert result.image_height == 80
    assert len(result.poses) == 1
    assert result.poses[0].bounding_box is not None
    assert result.poses[0].bounding_box.width == 36.0
    assert len(result.poses[0].keypoints) == 2


def test_rtmpose_empty_predictions(monkeypatch) -> None:
    captured: dict = {}
    _install_fake_mmpose(monkeypatch, captured, [])
    estimator = RTMPoseEstimator(PoseEstimatorConfig(pose_model='human'))
    result = estimator.estimate(np.zeros((32, 32, 3), dtype=np.uint8))
    assert result.poses == ()


def test_auto_device_falls_back_to_cpu_without_cuda() -> None:
    import types

    from rtmpose_ros.inference import _resolve_device

    fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
    assert _resolve_device('auto', fake_torch) == 'cpu'
    assert _resolve_device('', fake_torch) == 'cpu'


def test_cuda_request_without_gpu_is_a_clear_error() -> None:
    import types

    import pytest

    from rtmpose_ros.inference import _resolve_device

    fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
    with pytest.raises(RuntimeError, match='CUDA is not available'):
        _resolve_device('cuda:0', fake_torch)


@pytest.mark.skipif(
    os.environ.get('RUN_RTMPOSE_INFERENCE') != '1',
    reason='Requires the MMPose venv and downloaded checkpoints',
)
def test_rtmpose_cpu_inference_on_image() -> None:
    from pathlib import Path

    import cv2

    from rtmpose_ros.inference import create_estimator

    image_path = Path(os.environ.get('RTMPOSE_TEST_IMAGE', '/tmp/rtmpose_test.jpg'))
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    assert image is not None, f'missing test image at {image_path}'
    estimator = create_estimator(PoseEstimatorConfig(backend='rtmpose', device='cpu'))
    result = estimator.estimate(image)
    assert result.image_width == image.shape[1]
    assert result.image_height == image.shape[0]
    assert result.model_name == 'human'
    assert isinstance(result.poses, tuple)
