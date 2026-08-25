"""Run RTMPose or the mock estimator on an image, without ROS."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

# Allow running this file without installing the ROS package.
_PACKAGE_ROOT = Path(__file__).resolve().parents[1] / 'src' / 'rtmpose_ros'
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

from rtmpose_ros.inference import PoseEstimatorConfig, create_estimator  # noqa: E402
from rtmpose_ros.models import result_to_dict  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Run pose estimation on one image.')
    parser.add_argument('--image', required=True, help='Path to a BGR image file')
    parser.add_argument('--backend', default='rtmpose', choices=('rtmpose', 'mock'))
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--pose-model', default='human')
    parser.add_argument('--pose-weights', default='')
    parser.add_argument('--detector-model', default='')
    parser.add_argument('--detector-weights', default='')
    parser.add_argument('--keypoint-threshold', type=float, default=0.3)
    parser.add_argument('--detection-threshold', type=float, default=0.5)
    parser.add_argument('--output', default='', help='Write JSON result to this file')
    args = parser.parse_args(argv)

    image = cv2.imread(args.image, cv2.IMREAD_COLOR)
    if image is None:
        raise SystemExit(f'Could not read image: {args.image}')

    config = PoseEstimatorConfig(
        backend=args.backend,
        device=args.device,
        pose_model=args.pose_model,
        pose_weights=args.pose_weights,
        detector_model=args.detector_model,
        detector_weights=args.detector_weights,
        keypoint_threshold=args.keypoint_threshold,
        detection_threshold=args.detection_threshold,
    )
    estimator = create_estimator(config)
    result = estimator.estimate(np.asarray(image))
    payload = json.dumps(result_to_dict(result), indent=2)
    if args.output:
        Path(args.output).write_text(payload, encoding='utf-8')
    else:
        print(payload)
    print(
        f'{result.model_name}: {len(result.poses)} person(s) '
        f'in {result.image_width}x{result.image_height}',
        file=sys.stderr,
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
