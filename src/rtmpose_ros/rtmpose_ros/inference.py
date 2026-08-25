"""Pose estimators. This module must stay free of ROS publisher/subscriber code."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from rtmpose_ros.models import (
    COCO_17_KEYPOINT_NAMES,
    BoundingBox2D,
    Keypoint2D,
    PersonPose2D,
    PoseEstimationResult,
)


@dataclass(frozen=True)
class PoseEstimatorConfig:
    """Runtime settings for an estimator instance.

    ``pose_model`` / ``detector_model`` may be MMPose aliases (``human``),
    config names, or file paths. Empty weight strings let MMPose download
    the default checkpoint for that alias.
    """

    backend: str = 'rtmpose'
    device: str = 'cpu'
    pose_model: str = 'human'
    pose_weights: str = ''
    detector_model: str = ''
    detector_weights: str = ''
    keypoint_threshold: float = 0.3
    detection_threshold: float = 0.5
    skeleton_type: str = 'coco_17'


class PoseEstimator(ABC):
    """Estimate 2D person poses from a BGR uint8 image."""

    def __init__(self, config: PoseEstimatorConfig) -> None:
        self.config = config

    @abstractmethod
    def estimate(self, image: np.ndarray) -> PoseEstimationResult:
        raise NotImplementedError


class MockPoseEstimator(PoseEstimator):
    """Deterministic stand-in for tests. Does not load a neural network."""

    def estimate(self, image: np.ndarray) -> PoseEstimationResult:
        height, width = _image_hw(image)
        cx, cy = width * 0.5, height * 0.5
        keypoints = tuple(
            Keypoint2D(
                id=index,
                x=cx + (index - 8) * width * 0.02,
                y=cy + (index % 3 - 1) * height * 0.04,
                score=0.9,
                name=name,
            )
            for index, name in enumerate(COCO_17_KEYPOINT_NAMES)
        )
        person = PersonPose2D(
            person_id=0,
            score=0.9,
            keypoints=keypoints,
            bounding_box=BoundingBox2D(
                x=width * 0.25,
                y=height * 0.15,
                width=width * 0.5,
                height=height * 0.7,
                score=0.95,
            ),
        )
        return PoseEstimationResult(
            image_width=width,
            image_height=height,
            skeleton_type=self.config.skeleton_type,
            model_name='mock',
            poses=(person,),
            keypoint_names=COCO_17_KEYPOINT_NAMES
            if self.config.skeleton_type == 'coco_17'
            else tuple(kp.name for kp in keypoints),
        )


class RTMPoseEstimator(PoseEstimator):
    """RTMPose via MMPoseInferencer. Models are loaded once in the constructor."""

    def __init__(self, config: PoseEstimatorConfig) -> None:
        super().__init__(config)
        try:
            import torch
            from mmpose.apis import MMPoseInferencer
        except ImportError as exc:
            raise RuntimeError(
                f'MMPose import failed ({exc}). '
                'Use the /opt/rtmpose virtualenv from the Docker image.'
            ) from exc

        device = _resolve_device(config.device, torch)
        inferencer_kwargs: dict = {
            'pose2d': config.pose_model,
            'device': device,
        }
        if config.pose_weights:
            inferencer_kwargs['pose2d_weights'] = config.pose_weights
        if config.detector_model:
            inferencer_kwargs['det_model'] = config.detector_model
        if config.detector_weights:
            inferencer_kwargs['det_weights'] = config.detector_weights

        self._device = device
        self._inferencer = MMPoseInferencer(**inferencer_kwargs)

    def estimate(self, image: np.ndarray) -> PoseEstimationResult:
        height, width = _image_hw(image)
        result_generator = self._inferencer(
            image,
            show=False,
            return_vis=False,
            bbox_thr=self.config.detection_threshold,
        )
        raw = next(result_generator)
        poses = tuple(
            _person_from_prediction(index, prediction, self.config)
            for index, prediction in enumerate(_predictions_from_result(raw))
        )
        return PoseEstimationResult(
            image_width=width,
            image_height=height,
            skeleton_type=self.config.skeleton_type,
            model_name=self.config.pose_model,
            poses=poses,
            keypoint_names=COCO_17_KEYPOINT_NAMES
            if self.config.skeleton_type == 'coco_17'
            else (),
        )


def create_estimator(config: PoseEstimatorConfig) -> PoseEstimator:
    """Build an estimator from config. The ROS node should only call this."""
    backend = config.backend.strip().lower()
    if backend == 'mock':
        return MockPoseEstimator(config)
    if backend == 'rtmpose':
        return RTMPoseEstimator(config)
    raise ValueError(f'Unknown pose estimator backend: {config.backend}')


def _resolve_device(requested: str, torch_module) -> str:
    device = requested.strip().lower()
    if device in ('', 'auto'):
        return 'cuda:0' if torch_module.cuda.is_available() else 'cpu'
    if device.startswith('cuda') and not torch_module.cuda.is_available():
        raise RuntimeError(
            f'Requested device "{requested}" but CUDA is not available. '
            'Use device=cpu or omit the setting.'
        )
    return requested


def _image_hw(image: np.ndarray) -> tuple[int, int]:
    if image.ndim < 2:
        raise ValueError('Expected an image array with at least 2 dimensions')
    height, width = int(image.shape[0]), int(image.shape[1])
    return height, width


def _predictions_from_result(raw: dict) -> list:
    predictions = raw.get('predictions') or []
    if not predictions:
        return []
    first = predictions[0]
    if isinstance(first, dict):
        return list(predictions)
    return list(first)


def _person_from_prediction(
    person_id: int,
    prediction: dict,
    config: PoseEstimatorConfig,
) -> PersonPose2D:
    keypoints_raw = np.asarray(prediction.get('keypoints', []), dtype=float)
    scores_raw = np.asarray(prediction.get('keypoint_scores', []), dtype=float)
    if keypoints_raw.ndim == 1:
        keypoints_raw = keypoints_raw.reshape(-1, 2)

    keypoints: list[Keypoint2D] = []
    for index, point in enumerate(keypoints_raw):
        score = float(point[2]) if point.size >= 3 else (
            float(scores_raw[index]) if index < scores_raw.size else 0.0
        )
        if score < config.keypoint_threshold:
            continue
        name = (
            COCO_17_KEYPOINT_NAMES[index]
            if index < len(COCO_17_KEYPOINT_NAMES)
            else ''
        )
        keypoints.append(
            Keypoint2D(id=index, x=float(point[0]), y=float(point[1]), score=score, name=name)
        )

    bbox_score = prediction.get('bbox_score', prediction.get('score', 0.0))
    try:
        person_score = float(np.mean(scores_raw)) if scores_raw.size else float(bbox_score or 0.0)
    except TypeError:
        person_score = 0.0

    return PersonPose2D(
        person_id=person_id,
        score=person_score,
        keypoints=tuple(keypoints),
        bounding_box=_bbox_from_prediction(prediction),
    )


def _bbox_from_prediction(prediction: dict) -> BoundingBox2D | None:
    bbox = prediction.get('bbox')
    if bbox is None:
        return None
    values = np.asarray(bbox, dtype=float).reshape(-1)
    if values.size < 4:
        return None
    x1, y1, x2, y2 = (float(v) for v in values[:4])
    if x2 >= x1 and y2 >= y1:
        width, height = x2 - x1, y2 - y1
    else:
        width, height = x2, y2
    score_raw = prediction.get('bbox_score', 0.0)
    try:
        score = float(np.asarray(score_raw).reshape(-1)[0])
    except (TypeError, ValueError, IndexError):
        score = 0.0
    return BoundingBox2D(x=x1, y=y1, width=width, height=height, score=score)
