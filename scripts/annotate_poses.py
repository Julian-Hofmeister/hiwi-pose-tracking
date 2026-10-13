"""Annotate one or more images with RTMPose overlays (no ROS).

Examples (inside Docker):

    /opt/rtmpose/bin/python /ws/scripts/annotate_poses.py \\
      --input /ws/tmp/inbox/photo.jpg --output-dir /ws/tmp/out

    /opt/rtmpose/bin/python /ws/scripts/annotate_poses.py \\
      --input /ws/tmp/inbox --output-dir /ws/tmp/out

From Windows (repo root):

    docker compose -f docker/docker-compose.yml run --rm dev bash -lc \\
      "/opt/rtmpose/bin/python /ws/scripts/annotate_poses.py --input /ws/tmp/inbox --output-dir /ws/tmp/out"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

_PACKAGE_ROOT = Path(__file__).resolve().parents[1] / 'src' / 'rtmpose_ros'
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

from rtmpose_ros.inference import PoseEstimatorConfig, create_estimator  # noqa: E402
from rtmpose_ros.models import result_to_dict  # noqa: E402
from rtmpose_ros.visualization import draw_poses  # noqa: E402

_IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff'}

# Match src/rtmpose_ros/config/rtmpose.yaml defaults (fast CPU stack).
_DEFAULT_POSE_MODEL = 'rtmpose-t_8xb256-420e_body8-256x192'
_DEFAULT_DETECTOR_MODEL = 'rtmdet-t'


def _collect_images(path: Path) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() not in _IMAGE_SUFFIXES:
            raise SystemExit(f'Not an image file: {path}')
        return [path]
    if path.is_dir():
        images = sorted(
            p for p in path.iterdir()
            if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES
        )
        if not images:
            raise SystemExit(f'No images found in {path}')
        return images
    raise SystemExit(f'Input not found: {path}')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Run pose estimation and write overlay images.',
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Image file or directory of images',
    )
    parser.add_argument(
        '--output-dir',
        default='',
        help='Directory for annotated images (default: <repo>/tmp/out)',
    )
    parser.add_argument('--backend', default='rtmpose', choices=('rtmpose', 'mock'))
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--pose-model', default=_DEFAULT_POSE_MODEL)
    parser.add_argument('--pose-weights', default='')
    parser.add_argument('--detector-model', default=_DEFAULT_DETECTOR_MODEL)
    parser.add_argument('--detector-weights', default='')
    parser.add_argument('--keypoint-threshold', type=float, default=0.3)
    parser.add_argument('--detection-threshold', type=float, default=0.5)
    parser.add_argument(
        '--json',
        action='store_true',
        help='Also write a .json next to each overlay',
    )
    parser.add_argument(
        '--suffix',
        default='_pose',
        help='Suffix before extension for output files (default: _pose)',
    )
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[1]
    input_path = Path(args.input)
    output_dir = Path(args.output_dir) if args.output_dir else repo / 'tmp' / 'out'
    output_dir.mkdir(parents=True, exist_ok=True)

    images = _collect_images(input_path)
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
    print(
        f'Loading estimator (backend={config.backend}, model={config.pose_model}) …',
        file=sys.stderr,
    )
    estimator = create_estimator(config)

    for image_path in images:
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            print(f'SKIP unreadable: {image_path}', file=sys.stderr)
            continue
        started = time.monotonic()
        result = estimator.estimate(np.asarray(image))
        elapsed_ms = (time.monotonic() - started) * 1000.0
        overlay = draw_poses(image, result)
        out_name = f'{image_path.stem}{args.suffix}{image_path.suffix}'
        out_path = output_dir / out_name
        if not cv2.imwrite(str(out_path), overlay):
            raise SystemExit(f'Failed to write {out_path}')
        if args.json:
            json_path = output_dir / f'{image_path.stem}{args.suffix}.json'
            json_path.write_text(
                json.dumps(result_to_dict(result), indent=2),
                encoding='utf-8',
            )
        print(
            f'{image_path.name}: {len(result.poses)} person(s), '
            f'{elapsed_ms:.0f} ms → {out_path}',
            file=sys.stderr,
        )

    print(f'Done. Overlays in {output_dir}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
