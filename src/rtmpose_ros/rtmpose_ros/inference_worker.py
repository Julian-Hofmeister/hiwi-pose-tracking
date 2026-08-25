"""Stdin/stdout worker that loads RTMPose once and scores BGR frames.

This process is started with ``/opt/rtmpose/bin/python -m rtmpose_ros.inference_worker``.
It must not import ROS.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys

import numpy as np

from rtmpose_ros.inference import PoseEstimatorConfig, create_estimator
from rtmpose_ros.models import result_to_dict

_MAGIC = b'RTM1'
_HEADER = struct.Struct('>4sIII')


def _read_exact(stream, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining > 0:
        piece = stream.read(remaining)
        if not piece:
            raise EOFError('worker stdin closed')
        chunks.append(piece)
        remaining -= len(piece)
    return b''.join(chunks)


def _write_message(stream, payload: bytes) -> None:
    stream.write(_HEADER.pack(_MAGIC, 0, 0, len(payload)))
    stream.write(payload)
    stream.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='RTMPose inference worker')
    parser.add_argument('--backend', default='rtmpose')
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--pose-model', default='human')
    parser.add_argument('--pose-weights', default='')
    parser.add_argument('--detector-model', default='')
    parser.add_argument('--detector-weights', default='')
    parser.add_argument('--keypoint-threshold', type=float, default=0.3)
    parser.add_argument('--detection-threshold', type=float, default=0.5)
    args = parser.parse_args(argv)

    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    sys.stdout = sys.stderr

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
    try:
        estimator = create_estimator(config)
    except Exception as exc:  # noqa: BLE001
        _write_message(stdout, json.dumps({'error': str(exc)}).encode('utf-8'))
        return 1

    _write_message(stdout, json.dumps({'ready': True, 'model': config.pose_model}).encode('utf-8'))

    while True:
        try:
            header = _read_exact(stdin, _HEADER.size)
        except EOFError:
            return 0
        magic, height, width, nbytes = _HEADER.unpack(header)
        if magic != _MAGIC:
            _write_message(stdout, json.dumps({'error': 'bad magic'}).encode('utf-8'))
            return 1
        raw = _read_exact(stdin, nbytes)
        image = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 3)
        try:
            result = estimator.estimate(image)
            payload = result_to_dict(result)
        except Exception as exc:  # noqa: BLE001
            payload = {'error': str(exc)}
        _write_message(stdout, json.dumps(payload).encode('utf-8'))


if __name__ == '__main__':
    raise SystemExit(main())
